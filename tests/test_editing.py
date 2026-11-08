import io
import copy
import json
from pathlib import Path
import struct
import zipfile

import pytest

from defjam_caf.container import Container, SaveError
from defjam_caf.fields import apply_fields, read_fields, combine_styles
from defjam_caf.profiles import discover, directory_name, PROFILE_SIZE
from defjam_caf.storage import (save_profile, duplicate, export_profile, read_archive,
                                install_files, writer_lock, sha)
from defjam_caf._vendor.hd_assets import unswizzle, morton_offset
from defjam_caf.editor import Editor
from defjam_caf.appearance import Appearance


@pytest.fixture
def profile(tmp_path):
    title = tmp_path / "source" / "save" / "UserData" / "45410049"
    folder = title / directory_name("TEST")
    folder.mkdir(parents=True)
    payload = bytearray(PROFILE_SIZE)
    payload[:5] = b"TEST\0"
    payload[0x134:0x138] = bytes([0, 255, 255, 87])
    struct.pack_into("<6I", payload, 0x108, 3, 1, 1, 2, 1, 2)
    payload[0x4d87] = 87
    payload[0x3210:0x321b] = b"STORY BYTES"
    assert len(payload) == PROFILE_SIZE
    raw = Container(bytes(range(64)), bytes(payload)).encode()
    (folder / "TEST").write_bytes(raw)
    (folder / "SaveMeta.xbx").write_bytes("Name=TEST\r\n".encode("utf-16"))
    (folder / "saveimage.xbx").write_bytes(b"synthetic icon")
    return discover(title).profiles[0]


def test_exact_scalar_field_changes_preserve_unknown_story_and_bonus_bytes(profile):
    before = profile.container
    after = apply_fields(before, {"cash": 54321, "development": 1234, "stats": {"health": 50}})
    assert struct.unpack_from("<I", after.payload, 0x14)[0] == 54321
    assert struct.unpack_from("<I", after.payload, 0x1c)[0] == 1234
    assert struct.unpack_from("<I", after.payload, 0x100)[0] == 50
    allowed = set(range(0x14, 0x18)) | set(range(0x1c, 0x20)) | set(range(0x100, 0x104))
    assert all(a == b for i, (a, b) in enumerate(zip(before.payload, after.payload)) if i not in allowed)
    assert Container.read(after.encode()) == after


def test_style_edit_updates_combined_id_and_bonus_delta_but_preserves_story_style(profile):
    after = apply_fields(profile.container, {"styles": [1, 4]})
    assert after.payload[0x134:0x137] == bytes([1, 4, 255])
    assert after.payload[0x137] == combine_styles([1, 4])
    assert after.payload[0x4d87] == 87
    # Old bonuses included +(1,1,1,1,1,2) of accomplishments. Replace only styles.
    assert struct.unpack_from("<6I", after.payload, 0x108) == (1, 3, 4, 1, 2, 2)
    assert combine_styles([1, 4, 0]) == combine_styles([1, 0, 4])
    with pytest.raises(SaveError):
        combine_styles([1, 1])


@pytest.mark.parametrize("edits", [{"cash": -1}, {"cash": True}, {"development": 100001},
                                   {"stats": {"speed": 51}}, {"styles": []},
                                   {"styles": [7]}, {"unknown": 1}])
def test_invalid_edits_leave_original_unchanged(profile, edits):
    raw = profile.path.read_bytes()
    with pytest.raises(SaveError):
        apply_fields(profile.container, edits)
    assert profile.path.read_bytes() == raw


def test_backup_is_original_and_save_is_signed_with_stale_rejection(profile, tmp_path):
    original = profile.path.read_bytes()
    edited = apply_fields(profile.container, {"cash": 1000})
    backup = save_profile(profile, edited, tmp_path / "backups")
    name, saved, files = read_archive(backup)
    assert name == "TEST" and files["TEST"] == original
    assert Container.read(profile.path.read_bytes()) == edited
    with pytest.raises(SaveError, match="changed on disk"):
        save_profile(profile, edited, tmp_path / "backups")
    assert len(list((tmp_path / "backups").glob("*.djprofile"))) == 1


def test_full_transfer_and_duplicate_keep_story_and_refuse_collisions(profile, tmp_path):
    archive = tmp_path / "export.djprofile"
    export_profile(profile, profile.container, archive)
    name, save, files = read_archive(archive)
    imported = install_files(tmp_path / "destination" / "45410049", name, files)
    assert imported.read_bytes() == profile.path.read_bytes()
    assert (imported.parent / "saveimage.xbx").read_bytes() == b"synthetic icon"
    with pytest.raises(SaveError):
        install_files(imported.parent.parent, name, files)
    created = duplicate(profile, profile.container, "COPY1")
    duplicate_save = Container.read(created.read_bytes())
    assert duplicate_save.payload[:16] == b"COPY1" + bytes(11)
    assert duplicate_save.payload[16:] == save.payload[16:]
    assert discover(created.parent.parent).profiles[-1].name in {"TEST", "COPY1"}
    with pytest.raises(SaveError):
        duplicate(profile, profile.container, "COPY1")
    with pytest.raises(SaveError):
        export_profile(profile, profile.container, archive)


def test_import_rejects_traversal_and_corrupted_archive(profile, tmp_path):
    destination = tmp_path / "bad.djprofile"
    with zipfile.ZipFile(destination, "w") as z:
        z.writestr("manifest.json", json.dumps({"schema": 1, "title": "45410049", "name": "TEST",
                                                "files": {"../escape": {"sha256": sha(b"bad"), "size": 3}}}))
        z.writestr("profile/../escape", b"bad")
    with pytest.raises(SaveError):
        read_archive(destination)
    assert not (tmp_path / "escape").exists()


def test_writer_lock_is_exclusive_and_released_after_exception(profile):
    with writer_lock(profile.path.parent):
        with pytest.raises(SaveError):
            with writer_lock(profile.path.parent):
                pass
    with writer_lock(profile.path.parent):
        pass


def test_preview_overlays_never_enter_pending_edits_or_export(profile, tmp_path):
    editor = Editor(tmp_path / "workspace")
    editor.profile = profile
    editor.edits = {"cash": 1000}
    editor.history = [{"cash": 900}]
    appearance = Appearance.__new__(Appearance)
    appearance.by_key = {"try-on": {"key": "12:test", "value": 0x10000123, "color": 1}}
    appearance.outfit = lambda fields: copy.deepcopy(fields)
    editor.appearance = appearance
    class Capture:
        def compose(self, outfit):
            return {"outfit": outfit}
    editor.cache = Capture()
    staged = editor.current()
    before = profile.path.read_bytes()
    result = editor.preview({"part": "try-on"})
    assert result["outfit"]["caf_values"][12] == 0x10000123
    hidden = editor.preview({"part": "try-on"}, hide_clothes=True)
    assert all(hidden["outfit"]["caf_values"][i] == 0xffffffff for i in range(12, 20))
    assert hidden["outfit"]["caf_values"][29:] == read_fields(staged.payload)["caf_values"][29:]
    with pytest.raises(SaveError):
        editor.preview({"part": "unknown"})
    assert editor.current() == staged and editor.history == [{"cash": 900}]
    assert profile.path.read_bytes() == before
    destination = tmp_path / "staged-only.djprofile"
    editor.request("export", {"path": str(destination)})
    assert read_archive(destination)[1] == staged


@pytest.mark.parametrize("shape", [(4, 4, 1), (8, 4, 4), (4, 16, 4), (1, 16, 1), (32, 2, 4)])
def test_vectorized_swizzle_matches_scalar_address_reference(shape):
    w, h, bpp = shape
    raw = bytes((i * 17 + 3) % 256 for i in range(w * h * bpp))
    expected = b"".join(raw[morton_offset(x, y, w, h) * bpp:][:bpp] for y in range(h) for x in range(w))
    assert unswizzle(raw, w, h, bpp) == expected
