from contextlib import contextmanager
from pathlib import Path

import test_editing
from defjam_caf import storage
from defjam_caf.fields import read_fields

profile = test_editing.profile


def test_save_and_backup_leave_no_auxiliary_files_among_profiles(profile, tmp_path):
    before = {p.relative_to(profile.path.parent.parent) for p in profile.path.parent.parent.rglob("*")}
    storage.save_profile(profile, profile.container, tmp_path / "backups")
    after = {p.relative_to(profile.path.parent.parent) for p in profile.path.parent.parent.rglob("*")}
    assert after == before
    assert list(storage.default_lock_root().glob("*.lock"))
    assert read_fields(profile.container.payload)["has_fighter"]


def test_import_stages_as_sibling_and_removes_staging_after_collision(profile, tmp_path, monkeypatch):
    title = tmp_path / "destination/save/UserData/45410049"
    seen = []
    original = Path.rename

    def renamed(path, target):
        if path.name.startswith(".caf-import-"):
            seen.append(path)
            assert path.parent == title.parent
            assert not any(p.name.startswith(".caf-import-") for p in title.iterdir())
        return original(path, target)

    monkeypatch.setattr(Path, "rename", renamed)
    files = storage.profile_files(profile, profile.container)
    destination = storage.install_files(title, profile.name, files)
    assert destination.is_file() and len(seen) == 1
    assert not any(p.name.startswith(".caf-import-") for p in title.parent.iterdir())


def test_staging_is_cleaned_when_writer_lock_refuses(profile, tmp_path, monkeypatch):
    from defjam_caf.container import SaveError
    import pytest

    title = tmp_path / "destination/save/UserData/45410049"

    @contextmanager
    def refuse(folder):
        raise SaveError("Another editor is writing this profile")
        yield

    monkeypatch.setattr(storage, "writer_lock", refuse)
    with pytest.raises(SaveError, match="Another editor"):
        storage.install_files(title, profile.name, storage.profile_files(profile, profile.container))
    assert not list(title.iterdir())
    assert not any(p.name.startswith(".caf-import-") for p in title.parent.iterdir())
