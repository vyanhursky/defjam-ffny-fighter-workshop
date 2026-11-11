import struct

import pytest

from defjam_caf import backups
from defjam_caf.container import Container, SaveError
from defjam_caf.fields import apply_fields
from defjam_caf.profiles import discover, directory_name, PROFILE_SIZE
from defjam_caf.storage import save_profile


def make_profile(tmp_path, name="TEST"):
    title = tmp_path / "source" / "save" / "UserData" / "45410049"
    folder = title / directory_name(name)
    folder.mkdir(parents=True)
    payload = bytearray(PROFILE_SIZE)
    payload[:len(name) + 1] = name.encode() + b"\0"
    payload[0x134:0x138] = bytes([0, 255, 255, 87])
    struct.pack_into("<6I", payload, 0x108, 3, 1, 1, 2, 1, 2)
    payload[0x4d87] = 87
    (folder / name).write_bytes(Container(bytes(range(64)), bytes(payload)).encode())
    (folder / "SaveMeta.xbx").write_bytes(("Name=" + name + "\r\n").encode("utf-16"))
    return discover(title).profiles[0]


def cash(profile):
    return struct.unpack_from("<I", profile.container.payload, 0x14)[0]


def reload(profile):
    return discover(profile.path.parent.parent).profiles[0]


def test_restore_puts_back_the_saved_bytes_and_backs_up_what_it_replaced(tmp_path):
    profile = make_profile(tmp_path)
    root = tmp_path / "backups"
    original = cash(profile)
    save_profile(profile, apply_fields(profile.container, {"cash": 777}), root)
    profile = reload(profile)
    assert cash(profile) == 777
    rows = backups.entries(root, "TEST")
    assert len(rows) == 1 and rows[0]["id"].endswith(".djprofile") and rows[0]["when"].endswith("+00:00")

    replaced = backups.restore(profile, root, rows[0]["id"])

    after = reload(profile)
    assert cash(after) == original
    assert replaced.parent == root and replaced.name != rows[0]["id"]
    assert len(backups.entries(root, "TEST")) == 2
    # The restore itself can be undone with the backup it made.
    backups.restore(after, root, replaced.name)
    assert cash(reload(profile)) == 777


def test_entries_are_newest_first_per_profile_and_ignore_other_files(tmp_path):
    root = tmp_path / "backups"
    root.mkdir()
    for name in ("20260101T000000-TEST-aaaaaaaa.djprofile", "20260301T000000-TEST-bbbbbbbb.djprofile",
                 "20260201T000000-OTHER-cccccccc.djprofile", "notes.txt", "20260101T000000-TEST-zz.djprofile"):
        (root / name).write_bytes(b"x")
    assert [row["id"] for row in backups.entries(root, "TEST")] == [
        "20260301T000000-TEST-bbbbbbbb.djprofile", "20260101T000000-TEST-aaaaaaaa.djprofile"]
    assert backups.entries(tmp_path / "missing", "TEST") == []


@pytest.mark.parametrize("backup_id", ["../escape.djprofile", "..\\escape.djprofile", "notes.txt", "", None,
                                       "20260101T000000-TEST-aaaaaaaa.djprofile/.."])
def test_restore_refuses_anything_but_a_listed_backup_name(tmp_path, backup_id):
    profile = make_profile(tmp_path)
    with pytest.raises(SaveError):
        backups.restore(profile, tmp_path / "backups", backup_id)


def test_restore_refuses_a_missing_or_foreign_backup_and_leaves_the_save_alone(tmp_path):
    profile = make_profile(tmp_path)
    other = make_profile(tmp_path / "elsewhere", "OTHER")
    root = tmp_path / "backups"
    save_profile(other, apply_fields(other.container, {"cash": 5}), root)
    foreign = backups.entries(root, "OTHER")[0]["id"]
    before = profile.path.read_bytes()
    with pytest.raises(SaveError, match="different profile"):
        backups.restore(profile, root, foreign)
    with pytest.raises(SaveError, match="no longer exists"):
        backups.restore(profile, root, "20260101T000000-TEST-aaaaaaaa.djprofile")
    assert profile.path.read_bytes() == before
