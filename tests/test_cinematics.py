import base64
import copy
import hashlib
import pytest
from defjam_caf import performance, projects
from defjam_caf.container import SaveError
from test_performance import wav
from test_projects import fields


def settings():
    raw = wav()
    return dict(
        intro="CI_113A",
        voice=dict(preset="retail/blaze", banks={}, clips={"intro": base64.b64encode(raw).decode()}),
        cinematics={
            "intro": dict(
                voice_sha256=hashlib.sha256(raw).hexdigest(),
                source=dict(
                    format="fighter-cinematic-caf-performance-2",
                    template="CI_113A",
                    edits=[],
                    speech_tick=0,
                    mouth=dict(jaw=[[0, 0.0], [20, 0.5], [106, 0.0]], lips=[[0, 0], [20, 4], [106, 0]]),
                ),
            )
        },
    )


def test_authored_mouth_and_bound_voice_survive_project_save_reopen(tmp_path):
    p = projects.from_fields(fields()[0], "Example")
    p["performance"] = settings()
    path = tmp_path / "voice.ffnyfighter"
    projects.write(path, p)
    assert projects.read(path)[0]["performance"] == p["performance"]
    assert performance.status(p["performance"])["cinematics"] == p["performance"]["cinematics"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(intro="CI_132A"),
        lambda s: s["voice"]["clips"].clear(),
        lambda s: s["cinematics"]["intro"].update(voice_sha256="00" * 32),
        lambda s: s["cinematics"]["intro"]["source"].update(pointer=123),
        lambda s: s["cinematics"]["intro"]["source"]["mouth"]["jaw"].__setitem__(1, [20, float("nan")]),
        lambda s: s["cinematics"]["intro"]["source"]["mouth"]["lips"].__setitem__(1, [20, 1.5]),
        lambda s: s["cinematics"]["intro"]["source"]["mouth"]["jaw"].__setitem__(0, [0, 0.1]),
    ],
)
def test_rejects_desynchronization_or_unsafe_native_controls(mutate):
    value = copy.deepcopy(settings())
    mutate(value)
    with pytest.raises(SaveError):
        performance.validate(value)


def test_authored_entrance_and_final_attributes_survive_together(tmp_path):
    project = projects.from_fields(fields()[0], "Combined")
    project["fighter"]["final_stats"] = dict(upper=30, lower=47, speed=37, toughness=27, health=47, charisma=30)
    project["performance"] = settings()
    before = copy.deepcopy(project)
    target = tmp_path / "combined.ffnyfighter"
    projects.write(target, project)
    assert projects.read(target)[0] == before
    assert "victory" not in before["performance"]
    assert set(before["performance"]["voice"]["clips"]) == {"intro"}


def test_victory_and_approved_entrance_survive_together(tmp_path):
    value = settings()
    entrance = copy.deepcopy(value["cinematics"]["intro"])
    value["victory"] = "CE_113A"
    value["voice"]["clips"]["extro"] = value["voice"]["clips"]["intro"]
    value["cinematics"]["victory"] = copy.deepcopy(entrance)
    value["cinematics"]["victory"]["source"]["template"] = "CE_113A"
    performance.validate(value)
    project = projects.from_fields(fields()[0], "Both performances")
    project["performance"] = value
    path = tmp_path / "both.ffnyfighter"
    projects.write(path, project)
    assert projects.read(path)[0]["performance"] == value
    assert value["cinematics"]["intro"] == entrance
    bad = copy.deepcopy(value)
    bad["voice"]["clips"].pop("extro")
    with pytest.raises(SaveError):
        performance.validate(bad)
    bad = copy.deepcopy(value)
    bad["cinematics"]["victory"]["source"]["template"] = "CI_113A"
    with pytest.raises(SaveError):
        performance.validate(bad)


def test_export_refuses_entrance_only_runtime_for_victory(tmp_path, monkeypatch):
    from defjam_caf import fighter_mod, runtimes

    runtime = tmp_path / "runtime"
    for name in ("setup/fighter_caf.py", "scripts/fighter-contract.py"):
        f = runtime / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# invented fixture")
    value = settings()
    value["victory"] = "CE_113A"
    value["voice"]["clips"]["extro"] = value["voice"]["clips"]["intro"]
    value["cinematics"]["victory"] = copy.deepcopy(value["cinematics"]["intro"])
    value["cinematics"]["victory"]["source"]["template"] = "CE_113A"
    project = projects.from_fields(fields()[0], "Victory")
    project["performance"] = value
    monkeypatch.setattr(runtimes, "inspect", lambda *a, **k: dict(extensions=[]))
    with pytest.raises(SaveError, match="caf-victory-mouth-1"):
        fighter_mod.export_mod(project, tmp_path / "candidate.zip", runtime, tmp_path / "data", tmp_path / "work")


def hand_settings():
    value = settings()
    value["victory"] = "CE_113A"
    value["voice"]["clips"]["extro"] = value["voice"]["clips"]["intro"]
    value["cinematics"]["victory"] = copy.deepcopy(value["cinematics"]["intro"])
    source = value["cinematics"]["victory"]["source"]
    source["template"] = "CE_113A"
    source["left_hand"] = dict(
        format="fighter-native-left-hand-1",
        pose=[[0.0, 0.0, 0.0, 1.0] for _ in range(15)],
        envelope=[[0, 0], [19, 0], [24, 1], [39, 1], [44, 0], [106, 0]],
    )
    return value


def test_native_left_fingers_survive_project_without_changing_entrance(tmp_path):
    value = hand_settings()
    entrance = copy.deepcopy(value["cinematics"]["intro"])
    performance.validate(value)
    project = projects.from_fields(fields()[0], "Left fingers")
    project["performance"] = value
    path = tmp_path / "left.ffnyfighter"
    projects.write(path, project)
    assert projects.read(path)[0]["performance"] == value
    assert value["cinematics"]["intro"] == entrance


@pytest.mark.parametrize(
    "mutate",
    [
        lambda h: h.update(destinations=[4]),
        lambda h: h.update(pointer=123),
        lambda h: h["pose"].pop(),
        lambda h: h["pose"].__setitem__(0, [0.0, 0.0, 0.0, 0.0]),
        lambda h: h["pose"][0].__setitem__(0, float("nan")),
        lambda h: h["envelope"].__setitem__(0, [0, 1]),
        lambda h: h["envelope"].__setitem__(1, [19, True]),
    ],
)
def test_left_finger_document_rejects_unsafe_controls(mutate):
    value = hand_settings()
    mutate(value["cinematics"]["victory"]["source"]["left_hand"])
    with pytest.raises(SaveError):
        performance.validate(value)


def test_left_fingers_refuse_runtime_with_only_victory_mouth(tmp_path, monkeypatch):
    from defjam_caf import fighter_mod, runtimes

    runtime = tmp_path / "runtime"
    for name in ("setup/fighter_caf.py", "scripts/fighter-contract.py"):
        f = runtime / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# invented fixture")
    project = projects.from_fields(fields()[0], "Fingers")
    project["performance"] = hand_settings()
    monkeypatch.setattr(runtimes, "inspect", lambda *a, **k: dict(extensions=["caf-victory-mouth-1"]))
    with pytest.raises(SaveError, match="caf-left-fingers-1"):
        fighter_mod.export_mod(project, tmp_path / "candidate.zip", runtime, tmp_path / "data", tmp_path / "work")
