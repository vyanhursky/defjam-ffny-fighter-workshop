"""Standalone retail outfits preserve shared combat and independent appearance."""

import copy
import hashlib
import json

import pytest

from defjam_caf import retail, retail_outfits
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_retail_projects import pack


def session(tmp_path):
    root = tmp_path / "pack"
    pack(root)
    result = Editor(tmp_path / "work").retail
    result.request("import", dict(folder=root, fighter="river"))
    return result


def test_variants_edit_independently_share_combat_and_survive_save_undo(tmp_path):
    s = session(tmp_path)
    s.request("save", dict(path=tmp_path / "river.ffnyfighter"))
    s.request("outfit_rename", dict(name="Shirtless"))
    second = s.request("outfit_copy", {})["active_outfit"]
    s.request("outfit_rename", dict(name="Jacket"))
    s.request("component", dict(component="appearance", resource="retail/other-look"))
    s.request("stats", dict(stats={"health": 77}))
    s.request("outfit_select", dict(id="default"))
    assert s.snapshot()["document"]["definition"]["components"]["appearance"] == "example/body"
    assert s.snapshot()["document"]["definition"]["components"]["stats"] == {"health": 77}
    s.request("save", {})
    assert not s.request("outfit_select", dict(id=second))["dirty"]
    assert s.snapshot()["document"]["definition"]["components"]["appearance"] == "retail/other-look"
    assert s.snapshot()["document"]["definition"]["components"]["stats"] == {"health": 77}
    s.request("outfit_remove", {})
    assert len(s.snapshot()["outfits"]) == 1
    s.request("undo", {})
    assert len(s.snapshot()["outfits"]) == 2
    s.request("open", dict(path=tmp_path / "river.ffnyfighter"))
    assert s.snapshot()["outfits"] == [dict(id="default", name="Shirtless"), dict(id=second, name="Jacket")]
    assert s.snapshot()["active_outfit"] == "default"


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["outfits"][0].update(stats={}),
        lambda d: d["outfits"][0]["components"].update(voice="retail/example"),
        lambda d: d["outfits"][0].update(id="default"),
        lambda d: d["outfits"][0].update(name=""),
        lambda d: d.update(outfits=d["outfits"] * 3),
        lambda d: d.update(deployment=dict(mode="outfit", target="retail/example")),
    ],
)
def test_invalid_outfit_collections_are_refused(tmp_path, change):
    s = session(tmp_path)
    s.request("outfit_copy", {})
    document = copy.deepcopy(s.document)
    change(document)
    with pytest.raises(SaveError):
        retail.validate(document)


def test_three_outfit_limit_and_default_removal(tmp_path):
    s = session(tmp_path)
    s.request("outfit_copy", {})
    s.request("outfit_copy", {})
    with pytest.raises(SaveError, match="three outfits"):
        s.request("outfit_copy", {})
    s.request("outfit_select", dict(id="default"))
    with pytest.raises(SaveError, match="cannot be removed"):
        s.request("outfit_remove", {})


def test_collection_stage_uses_unique_bodies_and_preserves_transitive_asset_hashes(tmp_path, monkeypatch):
    s = session(tmp_path)
    source = s.document["resources"][0]["source"]
    source["shape_names"] = {"A001": "Abc1"}
    second = s.request("outfit_copy", {})["active_outfit"]
    s.request("component", dict(component="portrait", resource="retail/other"))
    before = copy.deepcopy(s.document)
    monkeypatch.setattr("defjam_caf.runtimes.inspect", lambda *args: {"extensions": ["standalone-retail-outfits-1"]})
    root = tmp_path / "stage"
    root.mkdir()
    native = s.stage(root, tmp_path, collection=True)
    assert s.document == before
    parent, child = native["fighters"]
    assert parent["inherits"] == "retail/example"
    assert child["inherits"] == child["outfit_of"] == "example/river"
    assert set(child["components"]) == {"appearance", "portrait"}
    appearances = [r for r in native["resources"] if r["kind"] == "appearance"]
    assert len(appearances) == 2
    assert appearances[0]["source"]["shape_names"] != appearances[1]["source"]["shape_names"]
    assert child["id"].endswith(second)
    for spec in retail.descriptors(native["resources"]):
        assert hashlib.sha256((root / spec["path"]).read_bytes()).hexdigest() == spec["sha256"]
    assert json.loads((root / "fighters.json").read_text()) == native
    imported = retail.import_pack(root, parent["id"])
    assert len(imported["outfits"]) == 1
    assert imported["outfits"][0]["id"] == second
    assert imported["outfits"][0]["name"] == child["name"]
    assert retail.import_pack(root, child["id"]) == imported


def test_old_runtime_allows_selected_preview_but_refuses_collection_export(tmp_path, monkeypatch):
    s = session(tmp_path)
    second = s.request("outfit_copy", {})["active_outfit"]
    s.request("component", dict(component="appearance", resource="retail/other"))
    monkeypatch.setattr("defjam_caf.runtimes.inspect", lambda *args: {"extensions": []})
    root = tmp_path / "preview"
    root.mkdir()
    assert (
        s.stage(root, tmp_path, include_performance=False)["fighters"][0]["components"]["appearance"] == "retail/other"
    )
    assert s.active_outfit == second
    with pytest.raises(SaveError, match="standalone outfit support"):
        s.stage(root, tmp_path, collection=True)


def test_resource_collection_keeps_shared_body_after_reimport(tmp_path):
    s = session(tmp_path)
    s.request("outfit_copy", {})
    # A new import gets a distinct resource and path. The copied outfit still
    # points at its original hash-bound source; no model is overwritten.
    s.document["resources"].append(dict(id="unused", kind="appearance", compatibility={}))
    s.document["assets"]["unused.bin"] = retail.blob(b"unused")
    s.prune_appearance_assets(s.document)
    assert [r["id"] for r in s.document["resources"]] == ["body"]
    assert set(s.document["assets"]) == {"body.bin"}
    assert retail_outfits.view(s.document, s.active_outfit)["definition"]["components"]["appearance"] == "example/body"
