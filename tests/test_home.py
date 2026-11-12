"""The Home screen's back end: recent projects, the home view, and leaving a project to start a workflow clean."""
import json

from defjam_caf import remembered
from defjam_caf.editor import Editor


def project_file(folder, name="fighter.ffnyfighter"):
    path = folder / name
    path.write_text("{}")
    return path


def test_recent_projects_are_newest_first_without_duplicates(tmp_path):
    first, second = project_file(tmp_path, "a.ffnyfighter"), project_file(tmp_path, "b.ffnyfighter")
    work = tmp_path / "work"
    remembered.add_recent(work, "caf", first)
    remembered.add_recent(work, "retail-new", second, "Second fighter")
    remembered.add_recent(work, "caf", first)
    rows = remembered.recents(work)
    assert [row["name"] for row in rows] == ["a", "Second fighter"]
    assert rows[0]["mode"] == "caf" and rows[1]["mode"] == "retail-new"


def test_a_recent_project_that_was_deleted_is_not_listed(tmp_path):
    gone = project_file(tmp_path)
    remembered.add_recent(tmp_path / "work", "caf", gone)
    gone.unlink()
    assert remembered.recents(tmp_path / "work") == []


def test_only_known_workflows_are_remembered_and_the_list_is_capped(tmp_path):
    work = tmp_path / "work"
    assert not remembered.add_recent(work, "story", project_file(tmp_path))
    for number in range(9):
        remembered.add_recent(work, "retail-edit", project_file(tmp_path, "p%d.ffnyfighter" % number))
    assert len(remembered.recents(work)) == remembered.RECENT_LIMIT
    assert json.loads((work / "remembered.json").read_text())["recent"][0]["name"] == "p8"


def test_a_damaged_list_reads_as_empty(tmp_path):
    (tmp_path / "remembered.json").write_text(json.dumps({"recent": [1, {"mode": "caf"}, {"mode": "nope", "path": "x"}]}))
    assert remembered.recents(tmp_path) == []


def test_the_home_view_carries_setup_and_recents_without_loading_game_data(tmp_path):
    editor = Editor(tmp_path / "work")
    view = editor.request("home", {})
    assert set(view) == {"setup", "recents", "version"}
    assert view["setup"]["ready"] is False and view["setup"]["data"] is None and view["recents"] == []


def test_the_setup_view_knows_a_remembered_data_folder_before_anything_is_loaded(tmp_path):
    data = tmp_path / "data"
    (data / "extracted").mkdir(parents=True)
    work = tmp_path / "work"
    remembered.remember(work, "data", data)
    assert Editor(work).setup_view()["data"] == str(data.resolve())


def test_leaving_a_retail_project_for_a_new_start_clears_it(tmp_path):
    editor = Editor(tmp_path / "work")
    session = editor.retail
    session.document = {"metadata": {}, "identity": {}}
    session.saved = session.document
    session.path = tmp_path / "x.ffnyfighter"
    editor.request("retail_close", {})
    assert session.document is None and session.path is None and session.saved is None
