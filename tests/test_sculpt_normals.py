import copy

import pytest

from defjam_caf import face_geometry as fg, projects, outfits
from defjam_caf.container import SaveError
from test_face_geometry import reference
from test_projects import fields


def correction():
    return dict(slot=3, rm=0, vertex=0, position=[0.0, 19.0, 1.0], original=1023, replacement=1023 << 11)


def sculpt():
    value = fg.empty(reference())
    value.update(schema=fg.NORMAL_SCHEMA, neck_normals=[correction()])
    return value


def test_v2_roundtrip_preserves_mixed_outfits_without_changing_source(tmp_path):
    project = projects.from_fields(fields()[0], "Example")
    project["face_sculpt"] = sculpt()
    project, second = outfits.add(project)
    project["outfits"][0]["face_sculpt"] = fg.empty(reference())
    before = copy.deepcopy(project)
    path = tmp_path / "normals.ffnyfighter"
    projects.write(path, project)
    loaded, _ = projects.read(path)
    assert loaded == before and project == before
    assert outfits.view(loaded, second)["face_sculpt"]["schema"] == fg.SCHEMA


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(neck_normals=[]),
        lambda v: v["neck_normals"].append(copy.deepcopy(v["neck_normals"][0])),
        lambda v: v["neck_normals"][0].update(slot=2),
        lambda v: v["neck_normals"][0].update(vertex=True),
        lambda v: v["neck_normals"][0].update(original=0),
        lambda v: v["neck_normals"][0].update(replacement=2**32),
        lambda v: v["neck_normals"][0].update(position=[0, float("nan"), 1]),
        lambda v: v["neck_normals"][0].update(extra="untrusted"),
    ],
)
def test_invalid_normal_records_are_refused(mutate):
    value = sculpt()
    mutate(value)
    with pytest.raises(SaveError):
        fg.validate(value)


def test_preview_is_position_and_original_normal_bound_and_does_not_mutate_cache():
    value = sculpt()
    model = dict(meshes=[dict(slot="3", rm=0, positions=[[0, 19, 1]], normals=[[1, 0, 0]])])
    before = copy.deepcopy(model)
    result = fg.apply_normals(model, value)
    assert result["meshes"][0]["normals"] == [[0, 1, 0]]
    assert model == before
    model["meshes"][0]["positions"][0][0] = 0.1
    with pytest.raises(SaveError, match="position differs"):
        fg.apply_normals(model, value)
    model = copy.deepcopy(before)
    model["meshes"][0]["normals"][0] = [0, 0, 1]
    with pytest.raises(SaveError, match="source differs"):
        fg.apply_normals(model, value)


def test_older_runtime_refuses_export_without_dropping_corrections(tmp_path):
    from defjam_caf import fighter_mod

    runtime = tmp_path / "runtime"
    (runtime / "setup").mkdir(parents=True)
    (runtime / "scripts").mkdir()
    (runtime / "setup/fighter_caf.py").touch()
    (runtime / "scripts/fighter-contract.py").touch()
    project = projects.from_fields(fields()[0], "Example")
    project["face_sculpt"] = sculpt()
    before = copy.deepcopy(project)
    with pytest.raises(SaveError, match="runtime with CAF sculpt normal corrections"):
        fighter_mod.export_mod(project, tmp_path / "out.zip", runtime, tmp_path / "data", tmp_path / "work")
    assert project == before and not (tmp_path / "out.zip").exists()


def test_readiness_checks_additional_outfits_for_the_runtime_extension(tmp_path, monkeypatch):
    from defjam_caf.editor import Editor

    project = projects.from_fields(fields()[0], "Example")
    project, _ = outfits.add(project)
    project["outfits"][0]["face_sculpt"] = sculpt()
    editor = Editor(tmp_path / "work")
    path = tmp_path / "project.ffnyfighter"
    projects.write(path, project)
    editor.open_project(path)
    setup = dict(ready=True, runtime=dict(features=dict(export=True), extensions=[]))
    monkeypatch.setattr(editor, "setup_view", lambda: setup)
    blocked = editor.request("export_checklist", {})
    assert not blocked["can_export"]
    assert next(row for row in blocked["checks"] if row["id"] == "sculpt_normals")["status"] == "fail"
    setup["runtime"]["extensions"] = [fg.NORMAL_EXTENSION]
    assert editor.request("export_checklist", {})["can_export"]


def test_reimporting_head_geometry_retains_existing_normal_corrections_and_undo(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from defjam_caf.editor import Editor

    project = projects.from_fields(fields()[0], "Example")
    project["face_sculpt"] = sculpt()
    path = tmp_path / "source.ffnyfighter"
    projects.write(path, project)
    editor = Editor(tmp_path / "work")
    editor.open_project(path)
    editor.appearance = editor.cache = SimpleNamespace()
    monkeypatch.setattr(editor, "snapshot", lambda: {})
    monkeypatch.setattr(fg, "template", lambda *a: reference())
    obj = tmp_path / "head.obj"
    obj.write_bytes(fg.obj(reference()).replace(b"v 1 1 0", b"v 1.2 1 0"))
    editor.request("face_import", {"path": str(obj)})
    imported = editor.project_document()["face_sculpt"]
    assert imported["schema"] == fg.NORMAL_SCHEMA
    assert imported["neck_normals"] == project["face_sculpt"]["neck_normals"]
    assert imported["meshes"] != project["face_sculpt"]["meshes"]
    editor.request("undo", {})
    assert editor.project_document() == project
