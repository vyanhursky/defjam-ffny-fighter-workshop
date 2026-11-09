"""Read-only, experimental CAF recovery from a PCSX2 EE-memory snapshot.

This is not a memory-card/profile converter. Only the observed PS2 CAF layout
is recognized; item references are translated by SODB identities, never by
assuming that PS2 and Xbox row ordinals happen to match.
"""
import binascii
import hashlib
import io
from pathlib import Path
import re
import struct
import zipfile

from ._vendor.caf_shop import Binary
from .assets import Database
from .container import SaveError
from .fields import STAT_KEYS, STYLE_NAMES, combine_styles
from .profiles import read_bounded
from .projects import from_fields, require, validate, SCHEMA2

EE_SIZE = 32 * 1024 * 1024
MAX_ARCHIVE = 128 * 1024 * 1024
APPEARANCE_OFFSET = 0x5560
COLOR_OFFSET = APPEARANCE_OFFSET + 38 * 4
RECORD_SIZE = 0x594C
TABLES_BY_SLOT = {**{s: 0x912016DD for s in range(12, 20)},
                  20: 0x7450591A, 21: 0x7450591A,
                  **{s: 0x426B8667 for s in (22, 23, 24, 25, 26, 28)},
                  **{s: 0x30948EA0 for s in range(29, 38)}}


def _member(archive, name, maximum):
    matches = [entry for entry in archive.infolist() if entry.filename == name]
    require(len(matches) == 1, "Missing or ambiguous savestate member: " + name)
    entry = matches[0]
    require(not entry.flag_bits & 1 and 0 <= entry.file_size <= maximum
            and 0 <= entry.compress_size <= MAX_ARCHIVE, "Unsupported savestate member size/encryption")
    if entry.compress_type == 93:
        try:
            import zstandard
        except ImportError as exc:
            raise SaveError("PCSX2 Zstandard snapshots need the optional dependency: pip install '.[ps2]'") from exc
        # Python 3.11–3.13 zipfile cannot read ZIP method 93. Use its validated
        # central directory offsets, verify the local header, then check CRC.
        archive.fp.seek(entry.header_offset)
        header = archive.fp.read(30)
        require(len(header) == 30 and header[:4] == b"PK\x03\x04", "Invalid savestate ZIP header")
        flags, method = struct.unpack_from("<HH", header, 6)
        name_size, extra_size = struct.unpack_from("<HH", header, 26)
        require(flags == entry.flag_bits and method == 93, "Inconsistent savestate ZIP header")
        local_name = archive.fp.read(name_size)
        require(local_name.decode("utf-8" if flags & 0x800 else "cp437") == name,
                "Inconsistent savestate ZIP member name")
        archive.fp.seek(extra_size, 1)
        compressed = archive.fp.read(entry.compress_size)
        require(len(compressed) == entry.compress_size, "Truncated savestate ZIP member")
        try:
            # Inspect the byte-valued frame window as well as bounding output.
            # zstandard 0.25's native/CFFI implementations pass max_window_size
            # to ZSTD_DCtx_setMaxWindowSize in bytes despite its KiB docstring.
            require(zstandard.get_frame_parameters(compressed).window_size <= EE_SIZE,
                    "PCSX2 Zstandard window exceeds 32 MiB")
            with zstandard.ZstdDecompressor(max_window_size=EE_SIZE).stream_reader(io.BytesIO(compressed)) as reader:
                raw = reader.read(maximum + 1)
        except zstandard.ZstdError as exc:
            raise SaveError("Invalid or oversized PCSX2 Zstandard frame: " + str(exc)) from exc
    else:
        require(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                "Unsupported savestate compression")
        with archive.open(entry) as stream:
            raw = stream.read(maximum + 1)
    require(len(raw) == entry.file_size and len(raw) <= maximum, "Savestate member size mismatch")
    require(binascii.crc32(raw) & 0xFFFFFFFF == entry.CRC, "Savestate member CRC mismatch")
    return raw


def memory(path):
    """Read a .p2s or a mod ZIP containing exactly one .p2s; extract no files."""
    raw = read_bounded(Path(path), MAX_ARCHIVE)
    source_hash = hashlib.sha256(raw).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as outer:
            names = [entry.filename for entry in outer.infolist()]
            if "eeMemory.bin" in names:
                state = raw
            else:
                states = [name for name in names if name.lower().endswith(".p2s")]
                require(len(states) == 1, "Mod archive must contain exactly one PCSX2 .p2s")
                state = _member(outer, states[0], MAX_ARCHIVE)
        with zipfile.ZipFile(io.BytesIO(state)) as archive:
            version = _member(archive, "PCSX2 Savestate Version.id", 256)
            require(len(version) >= 8 and version[:5] == b"\0\0S\x9av", "Unsupported PCSX2 version record")
            mem = _member(archive, "eeMemory.bin", EE_SIZE)
            require(len(mem) == EE_SIZE, "Expected the original 32 MiB PS2 EE memory layout")
        return mem, {"source_sha256": source_hash, "state_sha256": hashlib.sha256(state).hexdigest(),
                     "memory_sha256": hashlib.sha256(mem).hexdigest(),
                     "pcsx2_version_record_hex": version.hex()}
    except (zipfile.BadZipFile, UnicodeError, EOFError, RuntimeError) as exc:
        raise SaveError("Invalid PCSX2 archive: " + str(exc)) from exc


class MemoryDatabase(Binary):
    def __init__(self, data):
        super().__init__(data)
        require(self.cut(0, 8) == b"SODB\x02\0\0\0", "Unsupported PS2 database header")
        self.mapping(self.word(12), b"SKMA")
        self.tables = self.mapping(self.word(16), b"DATA")
        require(self.cut(self.word(20), 4) == b"STRT", "Unsupported PS2 database strings")
        self.cache = {}

    def records(self, table):
        if table not in self.cache:
            tag, index, _, count = self.words(self.tables[table][0], 4)
            require(tag == table, "Invalid PS2 database table")
            indexes = self.mapping(index)
            rows = self.mapping(indexes[table][0], table.to_bytes(4, "little"))
            require(len(rows) == count and all(len(row) == 1 for row in rows.values()),
                    "Invalid PS2 database row index")
            self.cache[table] = list(rows.items())
        return self.cache[table]

    def resolve(self, value, expected):
        ordinal, row = value >> 24, value & 0xFFFF
        tables = list(self.tables)
        require(ordinal < len(tables) and tables[ordinal] == expected, "Unsupported PS2 item table for CAF slot")
        records = self.records(expected)
        require(row < len(records), "Unsupported PS2 item row")
        ident, (offset,) = records[row]
        self.cut(offset, 4)
        return ident


def recover(mem, name):
    """Return the single consistent observed-layout record and its database.

    Multiple identical copies are acceptable. Conflicting live/archive copies
    remain ambiguous; the importer must never choose the first match silently.
    """
    require(re.fullmatch(r"[A-Z0-9 _-]{1,15}", name) is not None, "Use the exact uppercase PS2 fighter name (1–15 characters)")
    signature = name.encode("ascii").ljust(16, b"\0")
    records, databases = [], []
    for match in re.finditer(re.escape(b"SODB\x02\0\0\0"), mem):
        try:
            databases.append((match.start(), MemoryDatabase(mem[match.start():])))
        except (ValueError, KeyError, struct.error, SaveError):
            continue
    require(len(databases) == 1, "Missing or ambiguous intact FFNY SODB in PS2 memory")
    db_offset, database = databases[0]
    for match in re.finditer(re.escape(signature), mem):
        base = match.start()
        if base + RECORD_SIZE > len(mem):
            continue
        stats = list(struct.unpack_from("<5I", mem, base + 0xF0))
        slots = list(mem[base + 0x134:base + 0x137])
        styles = slots[:slots.index(255)] if 255 in slots else slots
        try:
            require(slots == styles + [255] * (3 - len(styles)), "Noncontiguous PS2 style slots")
            combined = combine_styles(styles)
            require(mem[base + 0x137] == combined and all(v <= 50 for v in stats), "Invalid PS2 training/style record")
            q = list(struct.unpack_from("<38I", mem, base + APPEARANCE_OFFSET))
            c = list(mem[base + COLOR_OFFSET:base + COLOR_OFFSET + 38])
            require(q[0] < 6 and 1 <= q[1] <= 16 and 1 <= q[5] <= 8
                    and all(1 <= v <= 32 for v in q[6:12]), "Unsupported PS2 CAF appearance")
            refs = []
            for slot, table in TABLES_BY_SLOT.items():
                if q[slot] == 0xFFFFFFFF:
                    continue
                ident = database.resolve(q[slot], table)
                refs.append({"slot": slot, "table": table, "record": ident, "color": (q[slot] >> 16) & 255})
            # The current Xbox CAF adapter cannot author a right wrist or a
            # nonempty direct teeth setting. Preserve them in inspection and
            # let the native recipe validator decide export support.
            fields = dict(stats=dict(zip(STAT_KEYS, stats)), styles=styles, caf_values=q, caf_colors=c, has_fighter=True)
            saved_finishers = struct.unpack_from("<4I", mem, base + 0x120)
            if saved_finishers != (0xFFFFFFFF,) * 4:
                # Original 20525 resolves these SODB references through the
                # 6FC83815 member before native paired-move setup.
                schema = database.mapping(database.word(12), b"SKMA")
                require(schema.get(0x47D305FD ^ 0x6FC83815) == (4, 2), "Unsupported PS2 finisher schema")
                require(all((value >> 16) & 255 == 0 for value in saved_finishers), "Unsupported PS2 finisher reference flags")
                fields["finishers"] = [f"{database.resolve(value, 0x47D305FD):08x}" for value in saved_finishers]
            records.append((base, fields, refs))
        except (SaveError, ValueError, KeyError, struct.error):
            continue
    require(bool(records), "No verified PS2 CAF record found for " + name)
    first = records[0]
    require(all(fields == first[1] and refs == first[2] for _, fields, refs in records),
            "Conflicting PS2 CAF copies; select a different snapshot")
    return first[1], first[2], {"profile_offsets": [hex(base) for base, _, _ in records],
                              "database_offset": hex(db_offset), "combined_style": combine_styles(first[1]["styles"])}


def inspect(path, name, data=None):
    mem, provenance = memory(path)
    try:
        fields, references, evidence = recover(mem, name)
        translated = []
        if data is not None:
            db = Database(Path(data) / "extracted")
            for reference in references:
                slot = reference["slot"]
                value = db.value_for(reference["table"], reference["record"], reference["color"])
                translated.append(dict(reference, source_value=fields["caf_values"][slot], target_value=value))
                fields["caf_values"][slot] = value
            if "finishers" in fields:
                schema = db.shop.mapping(db.shop.word(12), b"SKMA")
                require(schema.get(0x47D305FD ^ 0x6FC83815) == (4, 2), "Unsupported Xbox finisher schema")
                rows = dict(db.records(0x47D305FD))
                choices = []
                for identity in fields["finishers"]:
                    require(int(identity, 16) in rows, "Saved finisher is absent from the Xbox dump")
                    choice = db.shop.word(rows[int(identity, 16)][0] + 16)
                    require(choice < 82, "Saved finisher exceeds original paired resources")
                    choices.append(choice)
                evidence["finisher_choices"] = choices
        return {"schema": "pcsx2-caf-inspection-1", "name": name, **provenance, **evidence,
                "body_build": "ABCDEF"[fields["caf_values"][0]],
                "style_names": [STYLE_NAMES[s] for s in fields["styles"]],
                "fields": fields, "item_references": translated if data is not None else references,
                "xbox_items_verified": data is not None, "native_playtest": False,
                "textures_imported": False, "story_progress_included": False}
    except (ValueError, KeyError, IndexError, struct.error) as exc:
        raise SaveError("Unsupported PS2 CAF/database layout: " + str(exc)) from exc


def project(report, donor="retail/blaze"):
    require(report.get("xbox_items_verified") is True, "Verify item identities against the Xbox dump before creating a project")
    document = from_fields(report["fields"], report["name"],
                           {"donor": donor, "description": "Experimental PS2 CAF recovery. Original retail parts; native acceptance is recorded separately."})
    if "finishers" in report["fields"]:
        document["schema"] = SCHEMA2
        document["fighter"]["finishers"] = report["fields"]["finishers"][:]
    return validate(document)
