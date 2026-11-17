"""Versioned outfit collection; combat settings and fighter identity stay shared."""

import copy
import uuid

from . import projects
from .container import SaveError
from .contracts import AppearanceAssets, AppearanceKey, AssetKey, FighterProject, Outfit, OutfitEntry

DEFAULT = "default"
MAX_OUTFITS = 3
ASSETS: tuple[AssetKey, ...] = ("textures", "portrait", "ui_art", "face_sculpt")
APPEARANCE: tuple[AppearanceKey, ...] = ("caf_values", "caf_colors")


def entries(document: FighterProject) -> list[OutfitEntry]:
    result: list[OutfitEntry] = [{"id": DEFAULT, "name": document.get("outfit_name", "Outfit 1")}]
    result.extend({"id": row["id"], "name": row["name"]} for row in document.get("outfits", []))
    return result


def view(document: FighterProject, identity: str = DEFAULT) -> FighterProject:
    """Flatten a selected outfit for the existing single-CAF editor/preview."""
    result = copy.deepcopy(document)
    result.pop("outfits", None)
    result.pop("outfit_name", None)
    if identity != DEFAULT:
        selected = next((row for row in document.get("outfits", []) if row["id"] == identity), None)
        if selected is None:
            raise SaveError("This outfit is unavailable")
        for key in APPEARANCE:
            result["fighter"][key] = copy.deepcopy(selected[key])
        copy_assets(result, selected)
    return result


def replace_view(document: FighterProject, identity: str, selected: FighterProject) -> FighterProject:
    result = copy.deepcopy(document)
    result["identity"] = copy.deepcopy(selected["identity"])
    result["metadata"] = copy.deepcopy(selected["metadata"])
    result["fighter"]["stats"] = copy.deepcopy(selected["fighter"]["stats"])
    result["fighter"]["styles"] = selected["fighter"]["styles"][:]
    result["fighter"].pop("finishers", None)
    if "finishers" in selected["fighter"]:
        result["fighter"]["finishers"] = selected["fighter"]["finishers"][:]
    result["fighter"].pop("retail_moveset", None)
    if "retail_moveset" in selected["fighter"]:
        result["fighter"]["retail_moveset"] = selected["fighter"]["retail_moveset"]
    result["fighter"].pop("final_stats", None)
    if "final_stats" in selected["fighter"]:
        result["fighter"]["final_stats"] = copy.deepcopy(selected["fighter"]["final_stats"])
    if identity == DEFAULT:
        for key in APPEARANCE:
            result["fighter"][key] = selected["fighter"][key][:]
        copy_assets(result, selected)
    else:
        target = next((row for row in result.get("outfits", []) if row["id"] == identity), None)
        if target is None:
            raise SaveError("This outfit is unavailable")
        for key in APPEARANCE:
            target[key] = selected["fighter"][key][:]
        copy_assets(target, selected)
    return result


def upgrade(document: FighterProject) -> FighterProject:
    result = copy.deepcopy(document)
    result.setdefault("outfit_name", "Outfit 1")
    result.setdefault("outfits", [])
    return result


def add(document: FighterProject, source: str = DEFAULT) -> tuple[FighterProject, str]:
    projects.require(len(entries(document)) < MAX_OUTFITS, "A fighter supports up to three outfits")
    selected = view(document, source)
    result = upgrade(document)
    identity = "outfit-" + uuid.uuid4().hex[:12]
    row: Outfit = dict(
        id=identity,
        name="Outfit " + str(len(entries(document)) + 1),
        caf_values=selected["fighter"]["caf_values"][:],
        caf_colors=selected["fighter"]["caf_colors"][:],
    )
    copy_assets(row, selected)
    if source == DEFAULT:
        row.pop("ui_art", None)
    result["outfits"].append(row)
    return result, identity


def rename(document: FighterProject, identity: str, name: str) -> FighterProject:
    projects.require(
        type(name) is str
        and bool(name.strip())
        and len(name) <= 80
        and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in name),
        "Give the outfit a name (1–80 characters)",
    )
    result = upgrade(document)
    if identity == DEFAULT:
        result["outfit_name"] = name
    else:
        row = next((r for r in result["outfits"] if r["id"] == identity), None)
        if row is None:
            raise SaveError("This outfit is unavailable")
        row["name"] = name
    return result


def remove(document: FighterProject, identity: str) -> FighterProject:
    projects.require(identity != DEFAULT, "Keep the first outfit; additional outfits can be removed")
    result = copy.deepcopy(document)
    projects.require(any(row["id"] == identity for row in result.get("outfits", [])), "This outfit is unavailable")
    result["outfits"] = [row for row in result["outfits"] if row["id"] != identity]
    return result


def copy_assets(target: AppearanceAssets, source: AppearanceAssets) -> None:
    """Explicit keys preserve each optional asset's distinct value type."""
    target.pop("textures", None)
    target.pop("portrait", None)
    target.pop("ui_art", None)
    target.pop("face_sculpt", None)
    if "textures" in source:
        target["textures"] = copy.deepcopy(source["textures"])
    if "portrait" in source:
        target["portrait"] = source["portrait"]
    if "ui_art" in source:
        target["ui_art"] = copy.deepcopy(source["ui_art"])
    if "face_sculpt" in source:
        target["face_sculpt"] = copy.deepcopy(source["face_sculpt"])
