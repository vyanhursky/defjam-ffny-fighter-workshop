"""Choosing a game version once, and saying plainly what each version can do."""
import json

import pytest

from defjam_caf import runtimes
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor

FORMAT = "caf-fighter-1"
OLD = ("catalog", "tag-catalog", "voice-catalog", "validate-voice", "export-pair", "export-cinematic", "validate")
NEW = OLD + ("export-caf-portrait", "export-ui-reference", "export-retail-appearance", "preview-fighter",
             "workshop-catalog", "workshop-check", "workshop-audio", "workshop-animation", "workshop-export")


def source(path, commands, caf_format=None):
    (path / "scripts").mkdir(parents=True)
    listing = ", ".join("'%s'" % name for name in commands)
    (path / "scripts/fighter-contract.py").write_text("parser.add_argument('command', choices=(%s))\n" % listing)
    if caf_format:
        (path / "setup").mkdir()
        (path / "setup/fighter_caf.py").write_text("FORMAT = '%s'\n" % caf_format)
    return path


def app_folder(tmp_path):
    """Shaped like the Recomp app folder: data beside app/versions, an installed.json naming the running version."""
    root = tmp_path / "DefJamRecompiled"
    (root / "data/extracted").mkdir(parents=True)
    old = source(root / "app/versions/1.2.0-e950a7ff034a-4801dc171da7-attempt-8ccdd67d/source", OLD)
    new = source(root / "app/versions/1.3.0-aaaaaaaaaaaa-bbbbbbbbbbbb-attempt-11112222/source", NEW, FORMAT)
    (root / "app/versions/0.13.0-53d8d697e07b-be83eb981663-attempt-4cb64830/source").mkdir(parents=True)
    (root / "app/installed.json").write_text(json.dumps({"version": "1.2.0", "source": str(old)}))
    return root, old, new


def test_a_version_is_judged_feature_by_feature_from_its_files(tmp_path):
    old = runtimes.inspect(source(tmp_path / "old", OLD), FORMAT)
    assert old["usable"] and not old["complete"]
    assert old["features"] == {"export": False, "tools": False, "menu": False, "retail": False}
    assert "Custom Fighter" in old["missing"]["export"]
    new = runtimes.inspect(source(tmp_path / "new", NEW, FORMAT), FORMAT)
    assert new["complete"] and new["format"] == FORMAT
    # A version that has every command but writes a different recipe format cannot export, and says which one it uses.
    other = runtimes.inspect(source(tmp_path / "other", NEW, "caf-fighter-7"), FORMAT)
    assert other["features"]["retail"] and not other["features"]["export"]
    assert not runtimes.inspect(tmp_path / "nothing", FORMAT)["usable"]


def test_scan_lists_versions_newest_first_and_marks_the_installed_one(tmp_path):
    root, old, new = app_folder(tmp_path)
    found = runtimes.scan(root, FORMAT)
    assert [row["label"] for row in found["candidates"]] == ["Game 1.3.0", "Game 1.2.0"]
    assert [row["note"] for row in found["candidates"]] == ["", "installed"]
    assert found["data"] == str(root / "data") and found["current"] == "1.2.0"
    assert found["candidates"][0]["complete"] and not found["candidates"][1]["complete"]


def test_scan_accepts_one_version_or_a_developer_checkout(tmp_path):
    checkout = source(tmp_path / "checkout", NEW, FORMAT)
    rows = runtimes.scan(checkout, FORMAT)["candidates"]
    assert [row["label"] for row in rows] == ["Source checkout"] and rows[0]["complete"]
    assert runtimes.scan(tmp_path, FORMAT)["candidates"] == []


def test_require_explains_what_is_missing_and_what_to_do(tmp_path):
    old = source(tmp_path / "1.2.0-e950a7ff034a-4801dc171da7-attempt-1/source", OLD)
    with pytest.raises(SaveError, match="Retail fighter studio is not available in Game 1.2.0.*Game setup"):
        runtimes.require(old, "retail", FORMAT)
    with pytest.raises(SaveError, match="Game setup needed"):
        runtimes.require(None, "export", FORMAT)
    with pytest.raises(SaveError, match="does not look like a game version"):
        runtimes.require(tmp_path / "empty", "export", FORMAT)
    assert runtimes.require(source(tmp_path / "new", NEW, FORMAT), "retail", FORMAT)["complete"]


def test_default_folder_is_only_offered_where_the_app_installs(tmp_path):
    local = tmp_path / "AppData/Local"
    (local / "DefJamRecompiled").mkdir(parents=True)
    assert runtimes.default_folder(platform="win32", home=tmp_path, environ={"LOCALAPPDATA": str(local)}) == local / "DefJamRecompiled"
    assert runtimes.default_folder(platform="win32", home=tmp_path / "other", environ={}) is None
    assert runtimes.default_folder(platform="linux", home=tmp_path, environ={}) is None


def test_the_choice_is_remembered_and_actions_refuse_a_version_that_cannot_do_them(tmp_path):
    root, old, new = app_folder(tmp_path)
    workspace = tmp_path / "work"
    editor = Editor(workspace)
    editor.data = root / "data"
    assert editor.snapshot()["setup"]["runtime"] is None and not editor.snapshot()["setup"]["ready"]
    with pytest.raises(SaveError, match="Game setup needed"):
        editor.request("performance_connect", {})
    found = editor.request("setup_scan", {"folder": str(root)})
    assert len(found["candidates"]) == 2

    snapshot = editor.request("setup_use", {"runtime": str(old), "folder": str(root)})
    assert snapshot["setup"]["runtime"]["label"] == "Game 1.2.0" and snapshot["setup"]["folder"] == str(root)
    assert snapshot["setup"]["ready"]
    with pytest.raises(SaveError, match="Voice, entrance and AI tools is not available in Game 1.2.0"):
        editor.request("performance_connect", {})

    # A new session starts with the same version already chosen.
    assert Editor(workspace).runtime == old.resolve()
    editor.request("setup_use", {"runtime": str(new)})
    assert editor.snapshot()["setup"]["runtime"]["complete"]
    with pytest.raises(SaveError, match="not a game version"):
        editor.request("setup_use", {"runtime": str(tmp_path)})
