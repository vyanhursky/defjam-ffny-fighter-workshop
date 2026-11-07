#!/usr/bin/env python3
"""Local-only FFNY asset census, lossless SHPX export, and reproducible GPU jobs.

Requires Pillow in a separate tools environment. No assets/models enter source.
Archive source identities are provisional until correlated with runtime dumps.
"""
import argparse
from collections import Counter, deque
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import struct
import subprocess
import time

MAX_BLOB = 128 * 1024 * 1024
MAX_DIM = 4096


def digest(data):
    return hashlib.sha256(data).hexdigest()


def texture_id(fmt, width, height, pixels, palette=b"", row_texels=None):
    """v1: explicit LE descriptor, tightly packed source rows/blocks, palette."""
    return digest(b"XRTEX01\0" + struct.pack("<IIIII", fmt, width, height,
                                           len(palette) // 4, row_texels or width) + pixels + palette)


def archive_entries(blob):
    if blob[:4] not in (b"BIGF", b"BIG4") or len(blob) < 16:
        raise ValueError("Invalid BIG header")
    count = struct.unpack_from(">I", blob, 8)[0]
    if count > 100000:
        raise ValueError("Excessive archive directory")
    pos = 16
    for _ in range(count):
        if pos + 8 > len(blob):
            raise ValueError("Truncated archive directory")
        off, size = struct.unpack_from(">II", blob, pos)
        end = blob.find(b"\0", pos + 8, min(len(blob), pos + 4096))
        if end < 0 or off + size > len(blob):
            raise ValueError("Invalid archive entry")
        yield blob[pos + 8:end].decode("latin1"), blob[off:off + size]
        pos = end + 1


def unpack_refpack(blob):
    # Production limits and strict completeness around the existing decoder.
    sig = int.from_bytes(blob[:2], "big")
    step = 4 if sig & 0x8000 else 3
    pos = 2 + (step if sig & 0x0100 else 0)
    if len(blob) < pos + step:
        raise ValueError("Truncated RefPack header")
    expected = int.from_bytes(blob[pos:pos + step], "big")
    if expected > MAX_BLOB:
        raise ValueError("Excessive RefPack output")
    # The decoder must not grow beyond advertised size. Use a bounded decoder.
    pos += step
    out = bytearray()
    while pos < len(blob):
        b0 = blob[pos]; pos += 1
        if b0 < 0x80:
            b1 = blob[pos]; pos += 1
            run, length, dist = b0 & 3, ((b0 & 0x1c) >> 2) + 3, ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xc0:
            b1, b2 = blob[pos:pos + 2]; pos += 2
            run, length, dist = (b1 >> 6) & 3, (b0 & 0x3f) + 4, ((b1 & 0x3f) << 8) + b2 + 1
        elif b0 < 0xe0:
            b1, b2, b3 = blob[pos:pos + 3]; pos += 3
            run, length, dist = b0 & 3, ((b0 & 0xc) << 6) + b3 + 5, ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        else:
            run, length, dist = (((b0 & 0x1f) << 2) + 4 if b0 < 0xfc else b0 & 3), 0, 0
        if pos + run > len(blob) or len(out) + run + length > expected:
            raise ValueError("RefPack bounds exceeded")
        out.extend(blob[pos:pos + run]); pos += run
        if length and (not dist or dist > len(out)):
            raise ValueError("Invalid RefPack backreference")
        for _ in range(length):
            out.append(out[-dist])
        if b0 >= 0xfc:
            break
    if len(out) != expected:
        raise ValueError("Incomplete RefPack output")
    return bytes(out)


def walk(blob, label, depth=0, selected=None):
    if selected is not None and not any(p == label or p.startswith(label + "::") for p in selected):
        return  # Do not decompress unrelated members during a bounded audition.
    if depth > 12 or len(blob) > MAX_BLOB:
        raise ValueError("Container limit exceeded")
    if len(blob) >= 2 and int.from_bytes(blob[:2], "big") & 0x3eff == 0x10fb:
        yield from walk(unpack_refpack(blob), label, depth + 1, selected)
    elif blob[:4] in (b"BIG4", b"BIGF"):
        for name, data in archive_entries(blob):
            yield from walk(data, label + "::" + name, depth + 1, selected)
    else:
        yield label, blob


def morton_offset(x, y, w, h):
    offset, target, bit = 0, 0, 0
    while (1 << bit) < w or (1 << bit) < h:
        if (1 << bit) < w:
            offset |= ((x >> bit) & 1) << target; target += 1
        if (1 << bit) < h:
            offset |= ((y >> bit) & 1) << target; target += 1
        bit += 1
    return offset


def unswizzle(data, w, h, bpp):
    # Same Morton address calculation as upstream, vectorized for first-run CAF
    # indexing. Keep morton_offset as an independent scalar reference.
    import numpy as np
    x, y = np.meshgrid(np.arange(w, dtype=np.uint32), np.arange(h, dtype=np.uint32))
    offsets = np.zeros((h, w), dtype=np.uint32)
    target = bit = 0
    while (1 << bit) < w or (1 << bit) < h:
        if (1 << bit) < w:
            offsets |= ((x >> bit) & 1) << target
            target += 1
        if (1 << bit) < h:
            offsets |= ((y >> bit) & 1) << target
            target += 1
        bit += 1
    if len(data) % bpp or int(offsets.max()) >= len(data) // bpp:
        raise ValueError("Unsupported nonrectangular swizzle layout")
    return np.frombuffer(data, dtype=np.uint8).reshape(-1, bpp)[offsets.ravel()].tobytes()


def dxt_image(data, w, h, kind):
    from PIL import Image
    header = [0] * 31
    header[0:7] = [124, 0x81007, h, w, len(data), 0, 1]
    header[18:21] = [32, 4, int.from_bytes({0x60: b"DXT1", 0x61: b"DXT3", 0x62: b"DXT5"}[kind], "little")]
    header[26] = 0x1000
    return Image.open(io.BytesIO(b"DDS " + struct.pack("<31I", *header) + data)).convert("RGBA")


def shpx_images(blob, decode=True, indices=None):
    from PIL import Image
    if len(blob) < 16 or blob[:4] != b"SHPX":
        raise ValueError("Invalid SHPX")
    size, count = struct.unpack_from("<II", blob, 4)
    if size != len(blob) or count > 65536 or 16 + count * 8 > size:
        raise ValueError("Invalid SHPX directory bounds")
    for index in range(count):
        if indices is not None and index not in indices:
            continue
        name, offset = struct.unpack_from("<4sI", blob, 16 + index * 8)
        record = dict(index=index, name=name.decode("latin1"), offset=offset)
        try:
            if offset + 16 > size:
                raise ValueError("Truncated image header")
            kind = blob[offset]
            if kind == 0x2a:  # Palette directory targets are not textures.
                continue
            w, h = struct.unpack_from("<HH", blob, offset + 4)
            flags = struct.unpack_from("<I", blob, offset + 12)[0]
            record.update(type=kind, width=w, height=h, swizzled=bool(flags & 0x2000))
            if not w or not h or max(w, h) > MAX_DIM:
                raise ValueError("Invalid image dimensions")
            if flags >> 28:
                raise ValueError("Mip-bearing SHPX needs validated layout")
            data_offset = offset + (struct.unpack_from("<I", blob, offset + 16)[0] if flags & 0x1000 else 16)
            if data_offset < offset + 16:
                raise ValueError("Invalid indirect image pointer")
            palette = b""
            if kind in (0x60, 0x61, 0x62):
                n = ((w + 3) // 4) * ((h + 3) // 4) * (8 if kind == 0x60 else 16)
                fmt = {0x60: 0x0c, 0x61: 0x0e, 0x62: 0x0f}[kind]
            elif kind in (0x7b, 0x7d):
                n = w * h * (1 if kind == 0x7b else 4)
                fmt = 0x0b if kind == 0x7b else (0x06 if flags & 0x2000 else 0x12)
            else:
                raise ValueError("Unsupported SHPX type 0x%02x" % kind)
            if data_offset + n > size:
                raise ValueError("Truncated pixels")
            pixels = blob[data_offset:data_offset + n]
            if kind == 0x7b:
                pos, seen = offset, set()
                while pos not in seen:
                    seen.add(pos)
                    delta = int.from_bytes(blob[pos + 1:pos + 4], "little")
                    if not delta:
                        break
                    pos += delta
                    if pos + 16 > size or len(seen) > 64:
                        raise ValueError("Invalid attachment chain")
                    if blob[pos] == 0x2a:
                        colors = struct.unpack_from("<H", blob, pos + 4)[0]
                        if not 1 <= colors <= 256 or pos + 16 + colors * 4 > size:
                            raise ValueError("Invalid palette")
                        palette = blob[pos + 16:pos + 16 + colors * 4]
                        break
                if not palette:
                    raise ValueError("No BGRA palette")
                if not decode:
                    record.update(source_id=texture_id(fmt, w, h, pixels, palette), nv2a_format=fmt,
                                  palette_entries=len(palette) // 4, status="inventoried")
                    yield record, None
                    continue
                linear = unswizzle(pixels, w, h, 1) if flags & 0x2000 else pixels
                if max(linear) >= len(palette) // 4:
                    raise ValueError("Palette index out of bounds")
                bgra = b"".join(palette[i * 4:i * 4 + 4] for i in linear)
                image = Image.frombytes("RGBA", (w, h), bgra, "raw", "BGRA")
            elif kind == 0x7d:
                if not decode:
                    record.update(source_id=texture_id(fmt, w, h, pixels), nv2a_format=fmt, status="inventoried")
                    yield record, None
                    continue
                linear = unswizzle(pixels, w, h, 4) if flags & 0x2000 else pixels
                image = Image.frombytes("RGBA", (w, h), linear, "raw", "BGRA")
            else:
                if not decode:
                    record.update(source_id=texture_id(fmt, w, h, pixels), nv2a_format=fmt, status="inventoried")
                    yield record, None
                    continue
                image = dxt_image(pixels, w, h, kind)
            record.update(source_id=texture_id(fmt, w, h, pixels, palette), nv2a_format=fmt,
                          pixel_hash=digest(image.tobytes()), palette_entries=len(palette) // 4,
                          decoded_id=texture_id(0x12,w,h,image.tobytes("raw","BGRA")))
            yield record, image
        except (ValueError, IndexError, struct.error, OSError) as error:
            record["error"] = str(error)
            yield record, None
