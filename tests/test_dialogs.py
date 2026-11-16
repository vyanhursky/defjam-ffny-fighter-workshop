"""Native picker adaptation without real dialogs or original game data."""

import base64
import json
from types import SimpleNamespace

import pytest

import test_bridge
from defjam_caf.dialogs import Dialogs, QFileDialog, QInputDialog
from defjam_caf.editor import Editor
from defjam_caf.container import SaveError
from defjam_caf import projects

app = test_bridge.app


@pytest.fixture
def dialogs(app, tmp_path, monkeypatch):
    editor = Editor(tmp_path / "workspace")
    editor.profile = SimpleNamespace(name="CAFTEST")
    editor.discovery = object()
    bridge = SimpleNamespace(window=None, editor=editor, runtime_folder=lambda feature: "compatible-runtime")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: ("", ""))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: ("", ""))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: "")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a: ("", False))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a: ("", False))
    return Dialogs(bridge)


@pytest.mark.parametrize("action", sorted(set(Dialogs.SPECS) - {"choose_performance_tools", "choose_ui_retail"}))
def test_every_picker_can_cancel_without_scheduling_or_writing(dialogs, action):
    prepared = dialogs.prepare(action, {})
    assert prepared.action is None and prepared.result is None


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("choose_project", "open_project"),
        ("choose_new_project", "new_project"),
        ("choose_project_copy", "export"),
        ("choose_export", "export"),
        ("choose_face_import", "face_import"),
        ("choose_face_export", "face_export"),
        ("choose_retail_open", "retail_open"),
        ("choose_retail_copy", "retail_save"),
        ("choose_retail_export", "retail_export"),
        ("choose_import", "import"),
    ],
)
def test_file_picker_maps_to_domain_action_and_exact_path(dialogs, monkeypatch, action, expected):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: ("chosen-file", ""))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: ("chosen-file", ""))
    prepared = dialogs.prepare(action, {})
    assert prepared.action == expected and prepared.args == {"path": "chosen-file"}


def test_artwork_and_audio_forward_bytes_with_role_and_size_bounds(dialogs, monkeypatch, tmp_path):
    path = tmp_path / "invented.bin"
    path.write_bytes(b"invented source bytes")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (str(path), ""))
    atlas = dialogs.prepare("choose_project_atlas", {"slot": "d1"})
    assert atlas.action == "project_atlas" and atlas.args["slot"] == "d1"
    assert base64.b64decode(atlas.args["png"]) == path.read_bytes()
    voice = dialogs.prepare("choose_voice_clip", {"target": "event-slot"})
    assert voice.action == "performance_clip" and voice.args["target"] == "event-slot"
    with path.open("wb") as output:
        output.truncate(projects.MAX_ATLAS_BYTES + 1)
    with pytest.raises(SaveError, match="too large"):
        dialogs.prepare("choose_project_atlas", {"slot": "d1"})


def test_retail_import_choice_uses_bounded_manifest_and_stable_id(dialogs, monkeypatch, tmp_path):
    (tmp_path / "fighters.json").write_text(json.dumps({"fighters": [{"id": "stable-id", "name": "Example"}]}))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: str(tmp_path))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a: ("stable-id · Example", True))
    prepared = dialogs.prepare("choose_retail_import", {})
    assert prepared.action == "retail_import" and prepared.args == {"folder": str(tmp_path), "fighter": "stable-id"}


def test_existing_retail_save_skips_picker_and_duplicate_normalizes_id(dialogs, monkeypatch, tmp_path):
    dialogs.editor.retail.path = tmp_path / "existing.ffnyfighter"
    assert dialogs.prepare("choose_retail_save", {}).action == "retail_save"
    monkeypatch.setattr(QInputDialog, "getText", lambda *a: (" new123 ", True))
    assert dialogs.prepare("choose_duplicate", {}).args == {"name": "NEW123"}
