import base64
import copy
import io
import json

from PIL import Image
import pytest

from defjam_caf import projects, pngs, ui_art
from defjam_caf.editor import Editor
from defjam_caf.fields import read_fields
from defjam_caf.container import SaveError
from test_projects import fields


def png(color=(20, 40, 60, 255)):
    output = io.BytesIO()
    Image.new("RGBA", (256, 256), color).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def test_revalidation_reuses_verified_png_metadata_and_rechecks_changed_content(monkeypatch):
    pngs.clear_cache()
    document = projects.from_fields(fields()[0], "Example")
    document["ui_art"] = {"images": {"selector": png()}}
    calls = []
    original = Image.open

    def opened(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(Image, "open", opened)
    projects.validate(document)
    first = len(calls)
    assert first > 0
    for _ in range(4):
        projects.validate(document)
    assert len(calls) == first
    document["ui_art"]["images"]["selector"] = png((0, 0, 0, 0))
    with pytest.raises(SaveError, match="entirely transparent"):
        projects.validate(document)


def test_hot_keys_are_byte_bounded_and_metadata_remains_exact(monkeypatch):
    pngs.clear_cache()
    monkeypatch.setattr(pngs, "MAX_HOT_BYTES", 10)
    source = png()
    info = pngs.inspect_png(source, "portrait")
    assert pngs._hot_bytes <= 10 and not pngs._hot
    assert pngs.inspect_png(source, "portrait") == info
    assert len(pngs._cache) <= pngs.MAX_ENTRIES


def test_base_cache_tracks_in_place_content_changes_to_all_fighter_fields(tmp_path):
    editor = Editor(tmp_path)
    editor.project = projects.from_fields(fields()[0], "Example")
    editor.base()
    editor.project["fighter"]["stats"]["health"] = 42
    editor.project["fighter"]["styles"] = [1, 2]
    editor.project["fighter"]["caf_values"][0] = 4
    editor.project["fighter"]["caf_colors"][0] = 7
    result = read_fields(editor.base().payload)
    for key in projects.FIGHTER_FIELDS:
        assert result[key] == editor.project["fighter"][key]
    editor.outfit_draft = copy.deepcopy(editor.project)
    editor.outfit_draft["fighter"]["stats"]["health"] = 24
    assert read_fields(editor.base().payload)["stats"]["health"] == 24


def test_snapshot_excludes_asset_bytes_and_visual_key_ignores_nonvisual_edits(tmp_path):
    editor = Editor(tmp_path)
    editor.project = projects.with_atlas(projects.from_fields(fields()[0], "Example"), "a", base64.b64decode(png()))
    editor.project["portrait"] = png()
    first = editor.snapshot()
    assert png() not in json.dumps(first)
    assert not {"textures", "portrait"} & set(first["project"])
    editor.stage({"stats": {"health": 42}})
    assert editor.snapshot()["appearance_key"] == first["appearance_key"]
    editor.project["metadata"]["name"] = "Another name"
    assert editor.snapshot()["appearance_key"] == first["appearance_key"]
    editor.outfit_draft = ui_art.edit(editor.project, "default", role="selector", png=png())
    assert editor.snapshot()["appearance_key"] == first["appearance_key"]
    values = editor.current().payload
    assert values
    editor.project["fighter"]["caf_values"][0] = 4
    editor.outfit_draft = None
    assert editor.snapshot()["appearance_key"] != first["appearance_key"]
