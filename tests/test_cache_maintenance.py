import os
from pathlib import Path

import pytest

from defjam_caf import cache_maintenance as caches, projects
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields


def cache(workspace, number, mtime):
    root = workspace / "assets" / f"{number:064x}"
    (root / "catalog").mkdir(parents=True)
    path = root / "catalog/catalog.json"
    path.write_text("{}")
    (root / "invented-cache-data").write_bytes(b"12345")
    os.utime(path, (mtime, mtime))
    return root


def test_prune_keeps_active_and_most_recent_other_identity_and_cleans_failures(tmp_path):
    active, old, newest = [cache(tmp_path, i, i) for i in (1, 2, 3)]
    incomplete = active / ("incomplete-" + "a" * 32)
    incomplete.mkdir()
    (incomplete / "partial").write_text("invented")
    unknown = tmp_path / "assets/keep-my-notes"
    unknown.mkdir()
    caches.prune(tmp_path, active)
    assert active.is_dir() and newest.is_dir() and not old.exists() and not incomplete.exists()
    assert unknown.is_dir()
    assert caches.info(tmp_path)["bytes"] == 14


def test_clear_preserves_backups_projects_unknown_files_and_invalidates_size(tmp_path):
    cache(tmp_path, 1, 1)
    (tmp_path / "backups").mkdir()
    (tmp_path / "fighter.ffnyfighter").write_text("private project")
    assert caches.info(tmp_path)["bytes"] == 7
    caches.clear(tmp_path)
    assert caches.info(tmp_path)["bytes"] == 0
    assert (tmp_path / "backups").is_dir() and (tmp_path / "fighter.ffnyfighter").is_file()


def test_recursive_cleanup_refuses_outside_and_redirected_descendants(tmp_path, monkeypatch):
    workspace = tmp_path / "work"
    active = cache(workspace, 1, 1)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(SaveError, match="redirected"):
        caches.remove_owned(outside, workspace / "assets")
    target = active / "invented-cache-data"
    original = caches.redirected
    monkeypatch.setattr(caches, "redirected", lambda path: Path(path) == target or original(path))
    with pytest.raises(SaveError, match="redirected"):
        caches.clear(workspace)
    assert target.read_bytes() == b"12345"


def test_clear_action_preserves_unsaved_project_and_drafts(tmp_path):
    editor = Editor(tmp_path)
    editor.project = projects.from_fields(fields()[0], "Example")
    editor.stage({"stats": {"health": 42}})
    before = editor.project_document()
    cache(tmp_path, 1, 1)
    result = editor.request("cache_clear", {})
    assert editor.project_document() == before
    assert result["snapshot"]["dirty"]
    assert result["snapshot"]["setup"]["cache"]["bytes"] == 0
