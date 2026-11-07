import hashlib
from pathlib import Path
import struct

import pytest

from defjam_caf.container import Container, SaveError, digest
from defjam_caf.profiles import PROFILE_SIZE, directory_name, discover, metadata_name


def invented_profile(root: Path, name="TEST", *, legacy=False, opaque_word=4):
    folder = root / directory_name(name, legacy=legacy)
    folder.mkdir(parents=True)
    (folder / "SaveMeta.xbx").write_bytes(("Name=" + name + "\r\n").encode("utf-16"))
    payload = bytearray(PROFILE_SIZE)
    payload[:len(name)] = name.encode("ascii")
    struct.pack_into("<I", payload, 16, opaque_word)
    # Deliberately preserve nonzero unknown fields and padding.
    payload[1234:1240] = b"opaque"
    raw = Container(bytes(range(64)), bytes(payload)).encode()
    (folder / name).write_bytes(raw)
    return folder, raw


def test_codec_roundtrip_authenticates_both_chunks_and_the_header():
    value = Container(b"synthetic metadata", b"invented payload\x00\xff")
    raw = value.encode()
    assert Container.read(raw) == value
    assert Container.read(raw).encode() == raw
    # Mutate header length, metadata digest, payload digest, header digest,
    # metadata bytes and payload bytes independently.
    for position in (0, 4, 8, 12, 16, 36, 56, 76, len(raw) - 1):
        damaged = bytearray(raw)
        damaged[position] ^= 1
        with pytest.raises(SaveError):
            Container.read(bytes(damaged))
    with pytest.raises(SaveError):
        Container.read(raw + b"trailing bytes")
    with pytest.raises(SaveError):
        Container.read(raw[:75])


def test_signature_uses_standard_hmac_not_an_invented_cryptographic_primitive():
    # Independent standard-library construction of HMAC, not digest() itself.
    data = b"synthetic test vector"
    inner = hashlib.sha1(bytes([0x36]) * 64 + data).digest()
    expected = hashlib.sha1(bytes([0x5c]) * 64 + inner).digest()
    assert digest(data) == expected


def test_discovery_uses_the_metadata_named_file_and_never_changes_source(tmp_path):
    title = tmp_path / "save" / "UserData" / "45410049"
    folder, raw = invented_profile(title)
    (folder / "AAA").write_bytes(b"stale unrelated file")
    # A valid Options container must not become a CAF profile.
    options = title / directory_name("Options")
    options.mkdir()
    (options / "SaveMeta.xbx").write_bytes("Name=Options\r\n".encode("utf-16"))
    (options / "Options").write_bytes(Container(b"metadata", b"global options").encode())
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    for selected in (tmp_path, tmp_path / "save", tmp_path / "save" / "UserData", title):
        result = discover(selected)
        assert not result.issues
        assert [p.name for p in result.profiles] == ["TEST"]
        profile = result.profiles[0]
        assert profile.container.encode() == raw
        assert profile.extra_files == ("AAA",)
        assert profile.sha256 == hashlib.sha256(raw).hexdigest()
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_precise_legacy_folder_is_accepted_only_when_canonical_absent(tmp_path):
    title = tmp_path / "45410049"
    # UTF-16 arithmetic produces a different last nibble for this name.
    assert directory_name("VY2") == "005600590032"
    assert directory_name("VY2", legacy=True) == "005600590036"
    invented_profile(title, "VY2", legacy=True)
    result = discover(title)
    assert len(result.profiles) == 1 and result.profiles[0].directory_kind == "legacy"
    invented_profile(title, "VY2")
    result = discover(title)
    assert len(result.profiles) == 1 and result.profiles[0].directory_kind == "canonical"
    assert len(result.issues) == 1


def test_damaged_unsupported_and_misnamed_profiles_are_reported(tmp_path):
    title = tmp_path / "45410049"
    folder, raw = invented_profile(title, "OLD")
    save = Container.read(raw)
    (folder / "OLD").write_bytes(Container(save.metadata, save.payload[:-1]).encode())
    folder, raw = invented_profile(title, "BAD")
    damaged = bytearray(raw)
    damaged[-1] ^= 1
    (folder / "BAD").write_bytes(damaged)
    folder, raw = invented_profile(title, "NAME")
    save = Container.read(raw)
    payload = b"WRONG" + bytes(11) + save.payload[16:]
    (folder / "NAME").write_bytes(Container(save.metadata, payload).encode())
    result = discover(title)
    assert not result.profiles
    assert len(result.issues) == 3
    errors = " ".join(issue["error"] for issue in result.issues)
    assert "layout" in errors and "signatures" in errors and "disagrees" in errors


def test_unverified_payload_words_remain_opaque_instead_of_becoming_format_versions(tmp_path):
    title = tmp_path / "45410049"
    _, raw = invented_profile(title, opaque_word=1)
    result = discover(title)
    assert len(result.profiles) == 1
    assert not result.issues
    assert result.profiles[0].container.encode() == raw


@pytest.mark.parametrize("raw", [b"", b"Name=TEST", "Name=../BAD".encode("utf-16"),
                                  "Name=A\nName=B".encode("utf-16"), b"\xff\xfe\x01"])
def test_metadata_rejects_traversal_ambiguity_and_bad_encoding(raw):
    with pytest.raises(SaveError):
        metadata_name(raw)


def test_folder_that_is_not_a_valid_profile_is_not_silently_ignored(tmp_path):
    title = tmp_path / "45410049"
    (title / "not-a-profile").mkdir(parents=True)
    result = discover(title)
    assert not result.profiles
    assert len(result.issues) == 1
