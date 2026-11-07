#!/usr/bin/env python3
"""Read-only FFNY fighter static mesh conversion (own dump -> private GLB).

Supported EAGL ELF32 data resources only. No executable code, rig reconstruction,
game reimport, animation or material-shader emulation. Output MUST stay outside
the source tree. See docs/model-viewer.md for the measured layout and limits.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct

from PIL import Image
from .hd_assets import archive_entries, unpack_refpack, MAX_BLOB

VERSION = 2
from .fighter_catalog import FIGHTERS, MODEL_ARCHIVES, preview_omission

# Only these static resources live in a nested cinematic archive. Existing
# gameplay source routes and decoder semantics remain unchanged.



def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ModelError(ValueError):
    pass


class ElfData:
    """Bounds-checked ELF32 REL reader. Local relocations are resolved explicitly."""
    def __init__(self, blob):
        self.blob = blob
        if len(blob) < 52 or len(blob) > MAX_BLOB or blob[:7] != b"\x7fELF\x01\x01\x01":
            raise ModelError("Expected bounded little-endian ELF32")
        h = struct.unpack_from("<HHIIIIIHHHHHH", blob, 16)
        if h[0] != 1 or h[1] != 8 or h[7] != 52 or h[10] != 40 or not 1 <= h[11] <= 32 or h[12] >= h[11]:
            raise ModelError("Unsupported ELF resource header")
        self.cut(blob, h[5], h[10] * h[11])
        sections = [struct.unpack_from("<10I", blob, h[5] + i * 40) for i in range(h[11])]
        names = self.cut(blob, sections[h[12]][4], sections[h[12]][5])
        self.sections = []
        for s in sections:
            self.sections.append(dict(name=self.string(names, s[0]), type=s[1], flags=s[2],
                                      data=self.cut(blob, s[4], s[5]), link=s[6], info=s[7], size=s[5], entsize=s[9]))
        if any(s["flags"] & 4 or s["name"] == ".text" for s in self.sections):
            raise ModelError("Executable sections are not model data")
        self.data_index = next(i for i, s in enumerate(self.sections) if s["name"] == ".data")
        self.data = self.sections[self.data_index]["data"]
        st = next(s for s in self.sections if s["type"] == 2)
        if st["entsize"] != 16 or st["size"] % 16 or st["link"] >= len(sections):
            raise ModelError("Invalid ELF symbol table")
        strings = self.sections[st["link"]]["data"]
        self.symbols = []
        for p in range(0, st["size"], 16):
            n, v, size, info, other, section = struct.unpack_from("<IIIBBH", st["data"], p)
            self.symbols.append(dict(name=self.string(strings, n), value=v, size=size, section=section))
        self.relocs = {}
        for s in self.sections:
            if s["type"] != 9:
                continue
            if s["info"] != self.data_index or s["entsize"] != 8 or s["size"] % 8:
                raise ModelError("Unsupported relocation target")
            for p in range(0, s["size"], 8):
                off, info = struct.unpack_from("<II", s["data"], p)
                if info & 255 != 2 or info >> 8 >= len(self.symbols) or off in self.relocs:
                    raise ModelError("Unsupported or duplicate relocation")
                self.u(off)
                self.relocs[off] = self.symbols[info >> 8]

    @staticmethod
    def cut(blob, off, size):
        if off < 0 or size < 0 or off + size > len(blob):
            raise ModelError("Resource range is outside its section")
        return blob[off:off + size]

    @staticmethod
    def string(blob, off):
        end = blob.find(b"\0", off)
        if off < 0 or off >= len(blob) or end < 0:
            raise ModelError("Invalid string offset")
        return blob[off:end].decode("ascii")

    def unpack(self, fmt, off):
        self.cut(self.data, off, struct.calcsize(fmt))
        return struct.unpack_from(fmt, self.data, off)

    def u(self, off):
        return self.unpack("<I", off)[0]

    def ptr(self, off):
        s = self.relocs.get(off)
        if not s or s["section"] != self.data_index:
            raise ModelError("Expected a relocated pointer into model data")
        dest = s["value"] + self.u(off)
        self.cut(self.data, dest, 1)
        return dest

    def symbol(self, prefix):
        found = [s for s in self.symbols if s["name"].startswith(prefix) and s["section"] == self.data_index]
        if len(found) != 1:
            raise ModelError("Expected one " + prefix + " resource")
        return found[0]["value"]


def normal_111110(word):
    def component(value, bits):
        sign = 1 << (bits - 1)
        return max(-1, ((value & (sign - 1)) - (value & sign)) / (sign - 1))
    n = [component(word, 11), component(word >> 11, 11), component(word >> 22, 10)]
    length = math.sqrt(sum(v * v for v in n))
    if length < .1:
        raise ModelError("Invalid packed source normal")
    return [v / length for v in n]


def triangles_from_strip(strip, count):
    """Degenerate joins still advance parity; reject unsupported restart markers."""
    if any(i < 0 or i >= count for i in strip):
        raise ModelError("Triangle strip index outside vertex stream")
    out = []
    for i in range(2, len(strip)):
        a, b, c = strip[i - 2:i + 1]
        if len({a, b, c}) < 3:
            continue
        out.extend((b, a, c) if i % 2 else (a, b, c))
    return out


def index_stream(e, at, vertex_count, first_vertex_array):
    """Read the two audited strip layouts after an animation-buffer binding.

    Long layout: one draw-count entry, total indices, index pointer.
    Direct layout: index count/pointer, followed immediately by vertex fields.
    Verify those vertex fields to reject arbitrary or multi-draw layouts rather
    than interpreting unknown parameter bytes as index data.
    """
    tag=e.u(at+4)
    if tag==1:
        n,ip=e.u(at+12),e.ptr(at+16)
        if e.u(e.ptr(at+8))!=n:
            raise ModelError("Unsupported index header")
    else:
        n,ip=tag,e.ptr(at+8)
        if e.u(at+12)!=vertex_count or e.ptr(at+16)!=first_vertex_array:
            raise ModelError("Unsupported direct index header")
    if not 3<=n<=1_000_000:
        raise ModelError("Invalid index count")
    return list(e.unpack("<"+str(n)+"H",ip))


def decode(blob, name, source_id):
    e = ElfData(blob)
    vb = {}
    rm = {}
    for s in e.symbols:
        m = re.match(r"__VB:::__GPvb_(\d+)_(\d+)_", s["name"])
        if m:
            vb.setdefault(int(m[2]), []).append((int(m[1]), s["value"]))
        m = re.match(r"__RM:::__GP_RM_.+_(\d+)$", s["name"])
        if m:
            rm[int(m[1])] = s["value"]
    if not rm or len(rm) > 1024:
        raise ModelError("No supported render mesh resources")
    model = e.symbol("__Model:::")
    group_count = e.u(model + 0x9c)
    if not 1 <= group_count <= 128:
        raise ModelError("Invalid material group count")
    names, table = e.ptr(model + 0xa0), e.ptr(model + 0xcc) + 4
    groups = {}
    for i in range(group_count):
        label = e.string(e.data, e.ptr(names + i * 4))
        n = e.u(table); table += 4
        if n > len(rm):
            raise ModelError("Invalid render group size")
        for j in range(n):
            p = e.ptr(table + j * 4) - 0x38
            number = next((k for k, v in rm.items() if v == p), None)
            if number is None or number in groups:
                raise ModelError("Unresolved/duplicate render group")
            groups[number] = label
        table += n * 4
    meshes, skipped = [], []
    for number, p in sorted(rm.items()):
        label = groups.get(number)
        if not label:
            raise ModelError("Render mesh has no material group")
        refs = [(off, s["name"]) for off, s in e.relocs.items() if p <= off < p + 0xe0]
        parent = e.relocs[p + 0x1c]["name"]
        if parent == "ParentRM_DJFXSparkle_Skin" or label == "Direction":
            skipped.append(dict(group=label, rm=number, reason="Point-sprite sparkle" if "Sparkle" in parent else "Untextured direction helper"))
            continue
        textures={match[1] for _,ref in refs
                  if (match:=re.search(r"^__EAGL::TAR:::.*;SHAPENAME=([^;]+);",ref))}
        omission=preview_omission(label,textures,source_id)
        if omission:
            skipped.append(dict(group=label,rm=number,texture_ref=omission['texture_ref'],
                                reason=omission['reason'],limitation=omission['limitation']))
            continue
        if len(textures)>1:
            raise ModelError("Ambiguous primary texture binding")
        if parent not in ("ParentRM_IrradTexture_Skin", *("ParentRM_DJIrradTextureEnvmap_Skin" + str(i) for i in range(1, 5))):
            raise ModelError("Unsupported material shader: " + parent)
        state = next((s for _, s in refs if "SetPrimitiveType=" in s), "")
        # Some child render meshes inherit primitive state from their parent.
        if state and "PT_TRIANGLESTRIP" not in state:
            raise ModelError("Unsupported primitive topology")
        streams = sorted(vb[number])
        if len(streams) != 5:
            raise ModelError("Unsupported vertex stream count")
        arrays = []
        count = e.u(streams[0][1] + 4) // 12
        if not 3 <= count <= 65535:
            raise ModelError("Invalid vertex count")
        for (_, q), stride in zip(streams, (12, 8, 4, 4, 2)):
            size = e.u(q + 4)
            if e.u(q + 8) != stride or size < count * stride or size > count * stride + 2:
                raise ModelError("Unsupported vertex stream layout")
            arrays.append(e.ptr(q + 16))
            e.cut(e.data, arrays[-1], count * stride)
        positions = [list(e.unpack("<3f", arrays[0] + i * 12)) for i in range(count)]
        uv = [list(e.unpack("<2f", arrays[1] + i * 8)) for i in range(count)]
        normals = [normal_111110(e.u(arrays[3] + i * 4)) for i in range(count)]
        colors = [list(e.unpack("<4B", arrays[2] + i * 4)) for i in range(count)]
        # Locate index resources by the animation-buffer parameter, independent
        # of optional inherited state and shader constant parameter counts.
        animation = [off for off, s in refs if s == "__const MATRIX4:::EAGLAnimationBuffer"]
        if len(animation) != 1:
            raise ModelError("Expected one animation-buffer binding")
        at = animation[0]
        indices = triangles_from_strip(index_stream(e, at, count, arrays[0]), count)
        for i in range(0, len(indices), 3):
            indices[i], indices[i + 1] = indices[i + 1], indices[i]
        if not indices or any(not math.isfinite(v) or abs(v) > 10000 for a in positions + uv for v in a):
            raise ModelError("Invalid mesh coordinates")
        # Source strips face clockwise relative to the stored normals. Reverse
        # once for glTF CCW; keep coordinates and top-left UV convention.
        meshes.append(dict(name=label + " / RM" + str(number), group=label, rm=number,
                           positions=positions, uv=uv, normals=normals, colors=colors,
                           indices=indices, transparent="_ALPHA" in label or any("ABM_BLEND" in ref for _,ref in refs)))
        if textures:meshes[-1]['texture_ref']=next(iter(textures))
    all_pos = [p for m in meshes for p in m["positions"]]
    if not all_pos:raise ModelError("No retained primary-atlas meshes")
    bounds = [[min(p[i] for p in all_pos) for i in range(3)], [max(p[i] for p in all_pos) for i in range(3)]]
    return dict(schema=1, decoder=VERSION, name=name, source_id=source_id, source_sha256=sha(blob),
                meshes=meshes, bounds=bounds, skipped=skipped,
                vertices=len(all_pos), triangles=sum(len(m["indices"]) // 3 for m in meshes),
                limitations=["Static source rest pose; no animation or rig export", "Unlit RGB reference; studio lighting is approximate",
                             "Game specular/irradiance shaders and sparkle effects are not reproduced"]+
                            list(dict.fromkeys(s['limitation'] for s in skipped if 'limitation' in s)))
