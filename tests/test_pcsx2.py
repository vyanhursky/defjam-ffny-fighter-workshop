"""Invented EE memory and ZIP fixtures; no save/game bytes."""
import binascii
import copy
import hashlib
import io
import struct
import zipfile

import pytest

from defjam_caf import pcsx2, projects
from defjam_caf.container import SaveError


def synthetic_memory():
    data = bytearray(0x40000)
    base, db_base = 0x1000, 0x20000
    data[base:base + 16] = b"DEMO".ljust(16, b"\0")
    struct.pack_into("<5I", data, base + 0xF0, 12, 23, 34, 45, 50)
    data[base + 0x134:base + 0x138] = bytes([1, 0, 3, 101])
    struct.pack_into("<4I", data, base + 0x120, *([0xFFFFFFFF] * 4))
    q = [2, 5, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1] + [0xFFFFFFFF] * 26
    q[13] = 0x00030000  # source table 0, row 0, color 3
    struct.pack_into("<38I", data, base + pcsx2.APPEARANCE_OFFSET, *q)
    # Minimal invented SODB: empty schema, one clothing row, no strings.
    db = bytearray(256)
    struct.pack_into("<4s5I", db, 0, b"SODB", 2, 0, 24, 36, 136)
    struct.pack_into("<4s2I", db, 24, b"SKMA", 0, 1)
    table = 0x912016DD
    struct.pack_into("<4s4I", db, 36, b"DATA", 1, 1, table, 56)
    struct.pack_into("<4I", db, 56, table, 72, 0, 1)
    struct.pack_into("<4I", db, 72, 1, 1, table, 88)
    struct.pack_into("<5I", db, 88, table, 1, 1, 0xABCDEF, 128)
    db[136:140] = b"STRT"
    data[db_base:db_base + len(db)] = db
    return data, base, db_base


def zip_bytes(entries, method=zipfile.ZIP_STORED):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=method) as archive:
        for name, value in entries:
            archive.writestr(name, value)
    return stream.getvalue()


def zstd_zip(name, raw, oversized_window=False):
    zstandard = pytest.importorskip("zstandard")
    compressed = zstandard.ZstdCompressor(write_content_size=False).compress(raw)
    if oversized_window:
        # Non-single-segment frame: request a 64 MiB decoder window despite a
        # tiny output, exercising allocation admission independently of size.
        assert compressed[4] == 0
        compressed = compressed[:5] + bytes([128]) + compressed[6:]
    name = name.encode("ascii")
    crc = binascii.crc32(raw) & 0xFFFFFFFF
    local = struct.pack("<4s5H3I2H", b"PK\x03\x04", 20, 0, 93, 0, 0, crc,
                        len(compressed), len(raw), len(name), 0) + name + compressed
    central = struct.pack("<4s6H3I5H2I", b"PK\x01\x02", 20, 20, 0, 93, 0, 0, crc,
                          len(compressed), len(raw), len(name), 0, 0, 0, 0, 0, 0) + name
    end = struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, 1, 1, len(central), len(local), 0)
    return local + central + end


def test_recovers_exact_fighter_fields_and_item_identity():
    data, base, db = synthetic_memory()
    fields, refs, evidence = pcsx2.recover(bytes(data), "DEMO")
    assert fields["styles"] == [1, 0, 3] and evidence["combined_style"] == 101
    assert fields["stats"]["health"] == 50 and fields["caf_values"][0] == 2
    assert evidence["profile_offsets"] == [hex(base)] and evidence["database_offset"] == hex(db)
    assert refs == [dict(slot=13, table=0x912016DD, record=0xABCDEF, color=3)]
    assert set(fields) == {"stats", "styles", "caf_values", "caf_colors", "has_fighter"}


def test_identical_copies_are_reported_but_conflicting_copies_refused():
    data, base, _ = synthetic_memory()
    target = 0xA000
    data[target:target + pcsx2.RECORD_SIZE] = data[base:base + pcsx2.RECORD_SIZE]
    assert pcsx2.recover(bytes(data), "DEMO")[2]["profile_offsets"] == [hex(base), hex(target)]
    struct.pack_into("<I", data, target + 0xF0, 25)
    with pytest.raises(SaveError, match="Conflicting"):
        pcsx2.recover(bytes(data), "DEMO")


@pytest.mark.parametrize("change", [
    lambda d, b: d.__setitem__(slice(b + 0x134, b + 0x138), bytes([1, 0, 3, 100])),
    lambda d, b: d.__setitem__(slice(b + 0x134, b + 0x138), bytes([1, 255, 3, 98])),
    lambda d, b: struct.pack_into("<I", d, b + 0xF0, 51),
    lambda d, b: struct.pack_into("<I", d, b + pcsx2.APPEARANCE_OFFSET, 99),
    lambda d, b: struct.pack_into("<I", d, b + pcsx2.APPEARANCE_OFFSET + 13 * 4, 0x10000000),
    lambda d, b: struct.pack_into("<I", d, b + pcsx2.APPEARANCE_OFFSET + 13 * 4, 0x00000001),
])
def test_rejects_unverified_layouts_and_item_references(change):
    data, base, _ = synthetic_memory()
    change(data, base)
    with pytest.raises(SaveError, match="No verified"):
        pcsx2.recover(bytes(data), "DEMO")


def test_ambiguous_database_and_missing_fighter_refused():
    data, _, db = synthetic_memory()
    with pytest.raises(SaveError, match="No verified"):
        pcsx2.recover(bytes(data), "OTHER")
    data[db + 0x1000:db + 0x1100] = data[db:db + 256]
    with pytest.raises(SaveError, match="ambiguous"):
        pcsx2.recover(bytes(data), "DEMO")


def test_nested_snapshot_reads_memory_without_changing_archive(tmp_path):
    mem, _, _ = synthetic_memory()
    mem.extend(bytes(pcsx2.EE_SIZE - len(mem)))
    state = zip_bytes([("PCSX2 Savestate Version.id", b"\0\0S\x9av2.test\0"),
                       ("eeMemory.bin", bytes(mem))], zipfile.ZIP_DEFLATED)
    raw = zip_bytes([("mod/Save File/example.p2s", state), ("../unused.png", b"unused")])
    source = tmp_path / "source.zip"
    source.write_bytes(raw)
    recovered, receipt = pcsx2.memory(source)
    assert recovered == bytes(mem) and source.read_bytes() == raw
    assert receipt["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert list(tmp_path.iterdir()) == [source]


def test_zstd_zip_crc_and_size_validation():
    raw = b"invented snapshot data" * 10
    data = zstd_zip("memory", raw)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert pcsx2._member(archive, "memory", 1000) == raw
        with pytest.raises(SaveError, match="size"):
            pcsx2._member(archive, "memory", 4)
    corrupt = bytearray(data)
    central = corrupt.find(b"PK\x01\x02")
    struct.pack_into("<I", corrupt, central + 16, 123)
    with zipfile.ZipFile(io.BytesIO(corrupt)) as archive:
        with pytest.raises(SaveError, match="CRC"):
            pcsx2._member(archive, "memory", 1000)


def test_small_zstd_output_cannot_request_an_oversized_decoder_window():
    with zipfile.ZipFile(io.BytesIO(zstd_zip("memory", b"invented" * 100, True))) as archive:
        with pytest.raises(SaveError, match="window exceeds"):
            pcsx2._member(archive, "memory", 1000)


def test_populated_finisher_references_resolve_by_sodb_identity():
    data, base, db_base = synthetic_memory()
    db = bytearray(512)
    clothing, finisher = 0x912016DD, 0x47D305FD
    struct.pack_into('<4s5I', db, 0, b'SODB', 2, 0, 24, 48, 400)
    struct.pack_into('<4s5I', db, 24, b'SKMA', 1, 2, finisher ^ 0x6FC83815, 4, 2)
    struct.pack_into('<4s6I', db, 48, b'DATA', 2, 1, clothing, finisher, 80, 160)
    struct.pack_into('<4I', db, 80, clothing, 96, 0, 1)
    struct.pack_into('<4I', db, 96, 1, 1, clothing, 112)
    struct.pack_into('<5I', db, 112, clothing, 1, 1, 0xABCDEF, 140)
    struct.pack_into('<4I', db, 160, finisher, 176, 0, 4)
    struct.pack_into('<4I', db, 176, 1, 1, finisher, 192)
    struct.pack_into('<4s10I', db, 192, finisher.to_bytes(4, 'little'), 4, 1,
                     100, 200, 300, 400, 256, 280, 304, 328)
    db[400:404] = b'STRT'
    data[db_base:db_base + len(db)] = db
    struct.pack_into('<4I', data, base + 0x120, 0x01000003, 0x01000000, 0x01000002, 0x01000001)
    fields, _, _ = pcsx2.recover(bytes(data), 'DEMO')
    assert fields['finishers'] == ['00000190', '00000064', '0000012c', '000000c8']
    report = {'xbox_items_verified': True, 'fields': fields, 'name': 'DEMO'}
    assert pcsx2.project(report)['fighter']['finishers'] == fields['finishers']
    struct.pack_into('<I', data, base + 0x120, 0xFFFFFFFF)
    with pytest.raises(SaveError, match='No verified'):
        pcsx2.recover(bytes(data), 'DEMO')


def test_archive_ambiguity_and_truncated_memory_refused(tmp_path):
    source = tmp_path / "source.zip"
    source.write_bytes(zip_bytes([("one.p2s", b"one"), ("two.p2s", b"two")]))
    with pytest.raises(SaveError, match="exactly one"):
        pcsx2.memory(source)
    source.write_bytes(zip_bytes([("PCSX2 Savestate Version.id", b"\0\0S\x9av2.test\0"), ("eeMemory.bin", b"short")]))
    with pytest.raises(SaveError, match="32 MiB"):
        pcsx2.memory(source)


def test_translation_uses_database_identity_not_ps2_row_number(monkeypatch):
    mem, _, _ = synthetic_memory()
    monkeypatch.setattr(pcsx2, "memory", lambda _: (bytes(mem), {}))
    class Target:
        def __init__(self, path):
            pass
        def value_for(self, table, ident, color):
            assert (table, ident, color) == (0x912016DD, 0xABCDEF, 3)
            return 0x1003002A  # different target table and row ordinal
    monkeypatch.setattr(pcsx2, "Database", Target)
    report = pcsx2.inspect("unused", "DEMO", "target-data")
    assert report["fields"]["caf_values"][13] == 0x1003002A
    project = pcsx2.project(report)
    assert projects.validate(project) is project
    assert "cash" not in projects.encoded(project).decode()
    assert report["native_playtest"] is False and report["textures_imported"] is False
    report["xbox_items_verified"] = False
    with pytest.raises(SaveError, match="Verify item"):
        pcsx2.project(report)
