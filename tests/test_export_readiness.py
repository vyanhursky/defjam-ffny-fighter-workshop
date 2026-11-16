import copy
from types import SimpleNamespace

from defjam_caf import projects
from defjam_caf.editor import Editor
from test_projects import fields


def ready_editor(tmp_path, monkeypatch):
    editor = Editor(tmp_path / "workspace")
    path = tmp_path / "example.ffnyfighter"
    projects.write(path, projects.from_fields(fields()[0], "Example"))
    editor.open_project(path)
    monkeypatch.setattr(editor, "setup_view", lambda: dict(ready=True, runtime=dict(features=dict(export=True))))
    return editor


def test_readiness_accepts_donor_fallback_and_includes_pending_project_changes(tmp_path, monkeypatch):
    editor = ready_editor(tmp_path, monkeypatch)
    editor.stage({"stats": {"health": 42}})
    report = editor.request("export_checklist", {})
    assert report["can_export"]
    assert next(row for row in report["checks"] if row["id"] == "portrait")["status"] == "note"
    assert editor.snapshot()["dirty"]
    assert projects.read(editor.project_path)[0]["fighter"]["stats"]["health"] != 42


def test_readiness_links_invalid_details_and_missing_runtime_to_their_controls(tmp_path, monkeypatch):
    editor = ready_editor(tmp_path, monkeypatch)
    draft = copy.deepcopy(editor.project)
    draft["metadata"]["version"] = ""
    editor.metadata_edit = {key: draft[key] for key in ("metadata", "identity")}
    monkeypatch.setattr(editor, "setup_view", lambda: dict(ready=False, runtime=None))
    report = editor.request("export_checklist", {})
    assert not report["can_export"]
    assert {row["tab"] for row in report["checks"] if row["status"] == "fail"} == {"project", "setup"}
    assert next(row for row in report["checks"] if row["id"] == "valid")["detail"]


def test_donor_menu_uses_stable_retail_and_performance_catalog_identities(tmp_path):
    editor = Editor(tmp_path)
    editor.retail.catalog = {"fighters": [{"id": "blaze", "name": "Blaze"}]}
    assert editor.request("donors", {})["donors"] == [{"key": "retail/blaze", "label": "Blaze"}]
    editor.retail.catalog = None
    editor.performance_link = SimpleNamespace(catalog={"fighters": [{"key": "retail/pockets", "label": "Pockets"}]})
    assert editor.request("donors", {})["donors"] == [{"key": "retail/pockets", "label": "Pockets"}]
