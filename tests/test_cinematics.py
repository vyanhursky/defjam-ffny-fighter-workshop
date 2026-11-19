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
