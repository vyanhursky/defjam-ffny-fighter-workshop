"""Versioned outfit collection; combat settings and fighter identity stay shared."""
import copy
import uuid

from . import projects

DEFAULT = "default"
MAX_OUTFITS = 3
ASSETS = ("textures", "portrait", "ui_art", "face_sculpt")
APPEARANCE = ("caf_values", "caf_colors")


def entries(document):
    return [{"id": DEFAULT, "name": document.get("outfit_name", "Outfit 1")},
            *[{"id": row["id"], "name": row["name"]} for row in document.get("outfits", [])]]


def view(document, identity=DEFAULT):
    """Flatten a selected outfit for the existing single-CAF editor/preview."""
    result = copy.deepcopy(document)
    result.pop("outfits", None); result.pop("outfit_name", None)
    if document["schema"] == projects.SCHEMA3:
        result["schema"] = projects.SCHEMA2
    if identity != DEFAULT:
        selected = next((row for row in document.get("outfits", []) if row["id"] == identity), None)
        projects.require(selected is not None, "This outfit is unavailable")
        for key in APPEARANCE:
            result["fighter"][key] = copy.deepcopy(selected[key])
        for key in ASSETS:
            result.pop(key, None)
            if key in selected:
                result[key] = copy.deepcopy(selected[key])
    return result


def replace_view(document, identity, selected):
    result = copy.deepcopy(document)
    for key in ("identity", "metadata"):
        result[key] = copy.deepcopy(selected[key])
    for key in ("stats", "styles"):
        result["fighter"][key] = copy.deepcopy(selected["fighter"][key])
    result["fighter"].pop("finishers", None)
    if "finishers" in selected["fighter"]:
        result["fighter"]["finishers"] = selected["fighter"]["finishers"][:]
    result['fighter'].pop('retail_moveset',None)
    if 'retail_moveset' in selected['fighter']:
        result['fighter']['retail_moveset']=selected['fighter']['retail_moveset']
    if identity == DEFAULT:
        target = result["fighter"]
        assets = result
        if result["schema"] not in (projects.SCHEMA3,projects.SCHEMA4,projects.SCHEMA5,projects.SCHEMA6,projects.SCHEMA7):
            result["schema"] = selected["schema"]
    else:
        target = next((row for row in result.get("outfits", []) if row["id"] == identity), None)
        projects.require(target is not None, "This outfit is unavailable")
        assets = target
    for key in APPEARANCE:
        target[key] = copy.deepcopy(selected["fighter"][key])
    for key in ASSETS:
        assets.pop(key, None)
        if key in selected:
            assets[key] = copy.deepcopy(selected[key])
    if selected['schema'] in (projects.SCHEMA5,projects.SCHEMA6,projects.SCHEMA7):
        if result['schema'] not in (projects.SCHEMA6,projects.SCHEMA7):result['schema'] = selected['schema']
    return result


def upgrade(document):
    result = copy.deepcopy(document)
    result["schema"] = document['schema'] if document['schema'] in (projects.SCHEMA4,projects.SCHEMA5,projects.SCHEMA6,projects.SCHEMA7) else projects.SCHEMA3
    result.setdefault("outfit_name", "Outfit 1")
    result.setdefault("outfits", [])
    return result


def add(document, source=DEFAULT):
    projects.require(len(entries(document)) < MAX_OUTFITS, "A fighter supports up to three outfits")
    selected = view(document, source)
    result = upgrade(document)
    identity = "outfit-" + uuid.uuid4().hex[:12]
    row = dict(id=identity, name="Outfit " + str(len(entries(document)) + 1),
               **{key: copy.deepcopy(selected["fighter"][key]) for key in APPEARANCE})
    row.update({key: copy.deepcopy(selected[key]) for key in ASSETS if key in selected and (key!='ui_art' or source!=DEFAULT)})
    result["outfits"].append(row)
    return result, identity


def rename(document, identity, name):
    projects.require(type(name) is str and bool(name.strip()) and len(name) <= 80
                     and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in name),
                     "Give the outfit a name (1–80 characters)")
    result = upgrade(document)
    if identity == DEFAULT:
        result["outfit_name"] = name
    else:
        row = next((r for r in result["outfits"] if r["id"] == identity), None)
        projects.require(row is not None, "This outfit is unavailable")
        row["name"] = name
    return result


def remove(document, identity):
    projects.require(identity != DEFAULT, "Keep the first outfit; additional outfits can be removed")
    result = copy.deepcopy(document)
    projects.require(any(row["id"] == identity for row in result.get("outfits", [])), "This outfit is unavailable")
    result["outfits"] = [row for row in result["outfits"] if row["id"] != identity]
    return result
