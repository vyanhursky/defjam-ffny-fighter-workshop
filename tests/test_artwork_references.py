import base64
import copy
import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from defjam_caf import artwork_references, ui_art
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor


@pytest.fixture
def source(tmp_path, monkeypatch):
    runtime, game = tmp_path / "runtime", tmp_path / "game"
    for path in (runtime / "scripts/fighter-contract.py", game / "assets/djv2.sod", game / "screens/screens.viv"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"invented")
    monkeypatch.setattr("defjam_caf.runtimes.require", lambda *args: {"path": runtime})
    calls = []

    def contract(runtime, arguments, temporary, workspace):
        calls.append(arguments)
        output = Path(arguments[-1])
        output.mkdir()
        data = io.BytesIO()
        Image.new("RGBA", (24, 24), (30, 80, 140, 255)).save(data, format="PNG")
        raw = data.getvalue()
        images = {}
        for role in ui_art.PARTS:
            (output / (role + ".png")).write_bytes(raw)
            images[role] = dict(path=role + ".png", sha256=hashlib.sha256(raw).hexdigest())
        return dict(source=dict(donor=arguments[arguments.index("--donor") + 1], images=images))

    monkeypatch.setattr("defjam_caf.fighter_mod.contract", contract)
    return runtime, game, calls, contract


def test_stage_is_complete_cached_and_invalidates_changed_sources(tmp_path, source):
    runtime, game, calls, _ = source
    references = artwork_references.References()
    args = (runtime, game, "retail/blaze", tmp_path / "work", "caf-fighter-1")
    first = references.stage(*args)
    assert len(first["images"]) == 24 and set(first["images"]) == set(ui_art.PARTS)
    assert first["layouts"]["selector_2p"] == [24, 24]  # Original references may be smaller than import limits.
    assert base64.b64decode(first["images"]["selector_2p"].split(",")[1]).startswith(b"\x89PNG")
    first["images"].clear()
    assert len(references.stage(*args)["images"]) == 24 and len(calls) == 1
    (game / "screens/screens.viv").write_bytes(b"changed invented source")
    references.stage(*args)
    assert len(calls) == 2


@pytest.mark.parametrize("fault", ["hash", "escape", "missing", "donor", "size", "pixels"])
def test_bad_reference_output_is_refused(tmp_path, source, monkeypatch, fault):
    runtime, game, _, original = source

    def changed(*args):
        report = original(*args)
        images = report["source"]["images"]
        if fault == "hash":
            images["selector_2p"]["sha256"] = "0" * 64
        elif fault == "escape":
            images["selector_2p"]["path"] = "../outside.png"
        elif fault == "missing":
            images.pop("selector_2p")
        elif fault == "donor":
            report["source"]["donor"] = "retail/other"
        return report

    monkeypatch.setattr("defjam_caf.fighter_mod.contract", changed)
    if fault in ("size", "pixels"):
        monkeypatch.setattr(artwork_references, "MAX_BYTES" if fault == "size" else "MAX_PIXELS", 1)
    with pytest.raises(SaveError):
        artwork_references.References().stage(runtime, game, "retail/blaze", tmp_path / "work", "caf-fighter-1")


def test_retail_staging_preserves_project_and_tracks_selected_outfit_donor(tmp_path, source):
    runtime, game, calls, _ = source
    editor = Editor(tmp_path / "work")
    editor.runtime, editor.data = runtime, game.parent
    # Session.game expects the extracted folder; use a separate read-only fixture.
    editor.retail.game = lambda: game
    editor.request("retail_new", dict(donor="retail/blaze"))
    before = copy.deepcopy(editor.retail.document)
    history = copy.deepcopy(editor.retail.history)
    result = editor.request("retail_artwork_stage", {})
    assert result["donor"] == "retail/blaze"
    assert editor.retail.document == before and editor.retail.history == history
    editor.request("retail_outfit_copy", {})
    editor.request("retail_ui_settings", dict(donor="retail/other", hd_scale=4))
    assert editor.request("retail_artwork_stage", {})["donor"] == "retail/other"
    editor.request("retail_outfit_select", dict(id="default"))
    assert editor.request("retail_artwork_stage", {})["donor"] == "retail/blaze" and len(calls) == 2
