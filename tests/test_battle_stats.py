import pytest
from defjam_caf import projects, outfits, battle_stats
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from defjam_caf.fighter_mod import export_mod
from test_projects import fields

ATTRIBUTES = dict(zip(battle_stats.KEYS, (30, 47, 37, 27, 47, 30), strict=False))


def test_legacy_conversion_and_final_override_are_distinct():
    fighter = projects.from_fields(fields()[0], "Example")["fighter"]
    fighter.update(stats=dict(upper=30, lower=47, speed=37, toughness=27, health=47), styles=[1, 0, 3])
    assert battle_stats.effective(fighter) == dict(zip(battle_stats.KEYS, (30, 41, 31, 26, 38, 0), strict=False))
    fighter["final_stats"] = ATTRIBUTES
    assert battle_stats.effective(fighter) == ATTRIBUTES
    assert fighter["stats"]["lower"] == 47


@pytest.mark.parametrize(
    "bad", [None, {}, dict(ATTRIBUTES, charisma=True), dict(ATTRIBUTES, charisma=51), dict(ATTRIBUTES, health=-1)]
)
def test_invalid_final_stats_rejected_without_staging(tmp_path, bad):
    path = tmp_path / "fighter.ffnyfighter"
    projects.write(path, projects.from_fields(fields()[0], "Example"))
    editor = Editor(tmp_path / "workspace")
    editor.open_project(path)
    with pytest.raises(SaveError):
        editor.request("final_stats", {"values": bad if bad is not None else {}})
    assert not editor.snapshot()["dirty"] and not editor.history
    p = projects.read(path)[0]
    p["fighter"]["final_stats"] = bad
    with pytest.raises(SaveError):
        projects.validate(p)


def test_shared_stats_undo_reset_outfit_switch_save_and_reopen(tmp_path):
    p = projects.from_fields(fields()[0], "Example")
    p, other = outfits.add(p)
    path = tmp_path / "fighter.ffnyfighter"
    projects.write(path, p)
    editor = Editor(tmp_path / "workspace")
    editor.open_project(path)
    editor.stage({"stats": {"health": 42}})
    state = editor.request("final_stats", {"values": ATTRIBUTES})
    assert state["dirty"] and state["final_stats"] == ATTRIBUTES
    assert "Final battle attributes changed (all outfits)" in state["changes"]
    assert editor.project_document()["fighter"]["stats"]["health"] == 42
    editor.request("outfit_select", {"id": other})
    assert editor.snapshot()["final_stats"] == ATTRIBUTES
    editor.request("undo", {})
    # Outfit selection is navigation; Undo removes the last attribute edit.
    assert editor.snapshot()["final_stats"] is None
    editor.request("final_stats", {"values": ATTRIBUTES})
    editor.request("save", {})
    loaded = projects.read(path)[0]
    assert loaded["fighter"]["final_stats"] == ATTRIBUTES
    editor.open_project(path)
    state = editor.request("final_stats", {"values": None})
    assert state["final_stats"] is None and state["dirty"]
    assert editor.request("undo", {})["final_stats"] == ATTRIBUTES
    editor.request("final_stats", {"values": dict(ATTRIBUTES, charisma=40)})
    assert editor.request("reset", {})["final_stats"] == ATTRIBUTES
    loaded.pop("outfits")
    loaded.pop("outfit_name")
    path2 = tmp_path / "single.ffnyfighter"
    projects.write(path2, loaded)
    editor.open_project(path2)
    editor.request("final_stats", {"values": None})
    assert editor.snapshot()["dirty"] and editor.snapshot()["changes"]


def test_story_profile_has_no_final_stat_writer(tmp_path):
    editor = Editor(tmp_path / "workspace")
    with pytest.raises(SaveError, match="standalone"):
        editor.request("final_stats", {"values": ATTRIBUTES})


def test_export_to_old_runtime_fails_before_any_output(tmp_path):
    p = projects.from_fields(fields()[0], "Example")
    p["fighter"]["final_stats"] = ATTRIBUTES
    runtime = tmp_path / "old"
    (runtime / "setup").mkdir(parents=True)
    (runtime / "scripts").mkdir()
    (runtime / "setup/fighter_caf.py").write_text("FORMAT = 'caf-fighter-1'\n")
    (runtime / "scripts/fighter-contract.py").write_text("")
    destination = tmp_path / "fighter.zip"
    with pytest.raises(SaveError, match="caf-final-stats-1"):
        export_mod(p, destination, runtime, tmp_path, tmp_path / "workspace")
    assert not destination.exists()
