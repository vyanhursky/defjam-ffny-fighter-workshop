import base64
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from defjam_caf import projects
from defjam_caf.editor import Editor
from defjam_caf.container import SaveError
from test_audition_cache import wav


def session(tmp_path):
    editor = Editor(tmp_path / "work")
    editor.runtime = tmp_path / "runtime"
    editor.data = tmp_path / "data"
    (editor.data / "extracted").mkdir(parents=True)
    editor.performance_link = SimpleNamespace(catalog={}, call=lambda *args: dict(valid=True))
    editor.retail.catalog = {
        "fighters": [
            dict(id=name, name=name.title(), components=dict(stats=dict(health=health)))
            for name, health in (("first", 40), ("second", 90))
        ]
    }
    editor.request("retail_new", dict(donor="retail/first"))
    return editor


def test_shared_performance_edits_roundtrip_redact_audio_and_undo(tmp_path):
    editor = session(tmp_path)
    editor.request(
        "retail_performance_set", dict(section="voice", value=dict(preset="retail/second", banks={}, clips={}))
    )
    encoded = base64.b64encode(wav()).decode()
    snapshot = editor.request("retail_performance_clip", dict(target="Character:0", wav=encoded))
    assert "performance" not in snapshot["document"]
    assert snapshot["performance"]["settings"]["voice"]["clips"]["Character:0"]["samples"] == 240
    assert encoded not in json.dumps(snapshot)
    assert editor.request("retail_performance_audio", dict(override="Character:0"))["data"] == encoded
    path = tmp_path / "fighter.ffnyfighter"
    editor.request("retail_save", dict(path=str(path)))
    document = copy.deepcopy(editor.retail.document)
    editor.request("retail_performance_clear", dict(section="voice"))
    assert not editor.retail.document["performance"]
    editor.request("retail_undo", {})
    assert editor.retail.document == document
    assert projects.read(path)[0] == document
    editor.request("retail_open", dict(path=str(path)))
    assert editor.retail.document == document


def test_moveset_change_retains_stats_and_explicit_performance(tmp_path):
    editor = session(tmp_path)
    editor.request("retail_performance_set", dict(section="intro", value="CI_113A"))
    old = copy.deepcopy(editor.retail.document)
    result = editor.request("retail_moveset", dict(donor="retail/second"))["document"]
    assert result["definition"]["inherits"] == "retail/second"
    assert result["definition"]["components"]["stats"] == dict(health=40)
    assert result["asset_count"] == 0
    assert editor.retail.document["performance"] == old["performance"]
    editor.request("retail_undo", {})
    assert editor.retail.document == old


@pytest.mark.parametrize("mode", ["override", "outfit"])
def test_appearance_only_projects_keep_shared_performance(tmp_path, mode):
    editor = session(tmp_path)
    editor.request("retail_new", dict(donor="retail/first", mode=mode))
    with pytest.raises(SaveError, match="parent's performance"):
        editor.request("retail_performance_set", dict(section="intro", value="CI_113A"))
    with pytest.raises(SaveError, match="parent's combat"):
        editor.request("retail_moveset", dict(donor="retail/second"))


def test_export_uses_combat_family_and_stages_hash_bound_audio(tmp_path, monkeypatch):
    editor = session(tmp_path)
    editor.request(
        "retail_performance_set", dict(section="voice", value=dict(preset="retail/second", banks={}, clips={}))
    )
    original = copy.deepcopy(editor.retail.document)
    from defjam_caf import fighter_mod

    def contract(runtime, args, temporary, workspace):
        assert args[0] == "workshop-export"
        request = json.loads(Path(args[args.index("--workshop-request") + 1]).read_text())
        assert request["donor"] == "retail/first"  # Voice preset can differ from the event/motion namespace.
        output = Path(args[args.index("--workshop-out") + 1])
        output.mkdir()
        (output / "voice.wav").write_bytes(wav())
        pack = editor.retail.document["identity"]["pack"]
        return dict(
            resources=[
                dict(
                    id="performance-voice",
                    kind="voice",
                    compatibility=dict(events="retail/binding-first"),
                    source=dict(
                        format="invented-fixture",
                        intro=dict(path="performance/voice.wav", sha256=hashlib.sha256(wav()).hexdigest()),
                    ),
                )
            ],
            components=dict(voice=pack + "/performance-voice"),
        )

    monkeypatch.setattr(fighter_mod, "contract", contract)
    root = tmp_path / "staged"
    root.mkdir()
    native = editor.retail.stage(root, tmp_path)
    assert native["fighters"][0]["components"]["voice"].endswith("/performance-voice")
    assert (root / "workshop-performance/voice.wav").read_bytes() == wav()
    assert editor.retail.document == original  # Generated resources never leak into the editable source.
