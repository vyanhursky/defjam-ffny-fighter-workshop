"""Portable fighter recipes: no profile container, career, currency or source path."""
import copy
import base64
import io
import json
from pathlib import Path
import re
import uuid
import hashlib
import struct

from .container import Container, SaveError
from .fields import STAT_KEYS, apply_fields, combine_styles, read_fields
from .profiles import PROFILE_SIZE
from .storage import atomic_bytes, sha, writer_lock

# One project schema. Everything past identity, metadata and the four fighter fields is an optional section:
# finishers, a retail moveset, textures, a portrait, an outfit collection, UI artwork, a face sculpt and performance
# settings. Projects saved by earlier builds under the numbers below hold a subset of these sections, so they open
# unchanged and are stamped with the current schema the next time they are validated.
SCHEMA = "ffny-fighter-project-7"
EARLIER_SCHEMAS = tuple("ffny-fighter-project-%d" % n for n in range(1, 7))
READABLE_SCHEMAS = EARLIER_SCHEMAS + (SCHEMA,)
MAX_PROJECT = 384 * 1024 * 1024  # HD atlases of up to 2048px
ATLAS_SLOTS = ("a", "b", "c", "d", "d1", "d2")
FIGHTER_FIELDS = ("stats", "styles", "caf_values", "caf_colors")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def require(ok, message):
    if not ok:
        raise SaveError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate project field: " + key)
        result[key] = value
    return result


def validate(document):
    from .retail import READABLE_SCHEMAS as RETAIL_SCHEMAS, validate as retail_validate
    if type(document) is dict and document.get('schema') in RETAIL_SCHEMAS:
        return retail_validate(document)
    require(type(document) is dict and {"schema", "identity", "metadata", "fighter"} <= set(document)
            and set(document) <= {"schema", "identity", "metadata", "fighter", "portrait", "textures", "outfit_name", "outfits", "ui_art", "face_sculpt", "performance"},
            "Unsupported fighter project fields")
    require(document["schema"] in READABLE_SCHEMAS, "Unsupported fighter project version")
    if 'performance' in document:
        from .performance import validate as validate_performance
        validate_performance(document['performance'])
    has_outfits = bool({'outfits', 'outfit_name'} & set(document))
    if 'ui_art' in document:
        from . import ui_art
        ui_art.validate(document['ui_art'])
    identity, metadata, fighter = (document[k] for k in ("identity", "metadata", "fighter"))
    require(type(identity) is dict and set(identity) == {"pack", "fighter"}, "Invalid project identity")
    for value in identity.values():
        require(type(value) is str and len(value) <= 80 and SLUG.fullmatch(value) and value != "retail",
                "Stable IDs use lowercase letters, numbers and single hyphens; retail is reserved")
    require(type(metadata) is dict and set(metadata) == {"name", "author", "version", "description", "license", "donor"},
            "Invalid fighter project metadata")
    for key, limit in (("name", 80), ("author", 120), ("description", 4096), ("license", 512), ("version", 32), ("donor", 100)):
        value = metadata[key]
        require(type(value) is str and len(value) <= limit and not any(ord(c) < 32 or 0xd800 <= ord(c) <= 0xdfff for c in value),
                "Invalid project " + key)
    require(bool(metadata["name"].strip()), "Give the fighter a display name")
    require(VERSION.fullmatch(metadata["version"]), "Pack version must be major.minor.patch")
    require(re.fullmatch(r"retail/[a-z0-9]+(?:-[a-z0-9]+)*", metadata["donor"]), "Choose a retail presentation donor")
    require(type(fighter) is dict and set(FIGHTER_FIELDS) <= set(fighter)
            and set(fighter) <= set(FIGHTER_FIELDS) | {"finishers", "retail_moveset"},
            "Projects contain fighter fields only")
    if 'retail_moveset' in fighter:
        require(type(fighter['retail_moveset']) is str and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*',fighter['retail_moveset']),
                'Choose an original fighter moveset by stable identity')
    require(type(fighter["stats"]) is dict and set(fighter["stats"]) == set(STAT_KEYS), "Project needs all five training stats")
    require(type(fighter["styles"]) is list, "Project styles must be a list")
    combine_styles(fighter["styles"])
    # Reuse the editor's scalar/array checks without retaining any original save.
    apply_fields(empty_container(), {k: fighter[k] for k in FIGHTER_FIELDS})
    if "finishers" in fighter:
        require(type(fighter["finishers"]) is list and len(fighter["finishers"]) == 4
                and all(type(v) is str and re.fullmatch("[0-9a-f]{8}", v) for v in fighter["finishers"]),
                "Choose four retail finisher record identities")
    require(fighter["caf_values"][0] in range(6) and fighter["caf_values"][5] in range(1, 9),
            "Unsupported fighter body or face type")
    if 'face_sculpt' in document:
        from .face_geometry import validate as validate_face
        validate_face(document['face_sculpt'], fighter)
    if "portrait" in document:
        portrait_bytes(document["portrait"])
    if "textures" in document:
        textures = document["textures"]
        require(type(textures) is dict and set(textures) == {"appearance_sha256", "atlases"}, "Invalid project texture assets")
        require(textures["appearance_sha256"] == appearance_hash(fighter),
                "Appearance changed after atlas import; clear the texture atlases before importing the new outfit")
        require(type(textures["atlases"]) is dict and set(textures["atlases"]) <= set(ATLAS_SLOTS), "Invalid project atlas slots")
        for value in textures["atlases"].values():
            atlas_bytes(value)
    if has_outfits:
        from . import outfits
        require({"outfit_name", "outfits"} <= set(document), "A project with outfits needs both a default outfit name and an outfit list")
        require(type(document["outfits"]) is list and len(document["outfits"]) < outfits.MAX_OUTFITS,
                "A fighter supports one to three outfits")
        def name_valid(value):
            return type(value) is str and bool(value.strip()) and len(value) <= 80 and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value)
        require(name_valid(document["outfit_name"]), "Invalid outfit name")
        seen = {outfits.DEFAULT}
        for row in document["outfits"]:
            require(type(row) is dict and {"id", "name", "caf_values", "caf_colors"} <= set(row)
                    and set(row) <= {"id", "name", "caf_values", "caf_colors", "textures", "portrait", "ui_art", "face_sculpt"}, "Invalid outfit fields")
            require(type(row["id"]) is str and len(row["id"]) <= 80 and SLUG.fullmatch(row["id"])
                    and row["id"] not in seen, "Outfit IDs must be unique stable slugs")
            require(name_valid(row["name"]), "Invalid outfit name")
            seen.add(row["id"])
            validate(outfits.view(document, row["id"]))
    from . import ui_art
    ui_art.check_budget(document)
    document["schema"] = SCHEMA
    return document


def appearance_hash(fields):
    return hashlib.sha256(json.dumps({k: fields[k] for k in ("caf_values", "caf_colors")},
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atlas_bytes(value):
    from PIL import Image
    require(type(value) is str and len(value) <= 22_369_624, "Atlas PNG is too large")
    try:
        raw = base64.b64decode(value, validate=True)
        require(len(raw) <= 16 * 1024 * 1024, "Atlas PNG is too large")
        with Image.open(io.BytesIO(raw)) as image:
            require(image.format == "PNG" and image.width == image.height and image.width in (256,512,1024,2048), "Import a square 256, 512, 1024 or 2048 PNG atlas")
            image.verify()
    except (ValueError, OSError) as exc:
        raise SaveError("Invalid atlas PNG: " + str(exc)) from exc
    return raw


def with_atlas(document, slot, raw):
    require(slot in ATLAS_SLOTS, "Choose atlas a, b, c, d, d1 or d2")
    result = copy.deepcopy(validate(document))
    value = base64.b64encode(raw).decode("ascii")
    atlas_bytes(value)
    textures = result.setdefault("textures", {"appearance_sha256": appearance_hash(result["fighter"]), "atlases": {}})
    textures["atlases"][slot] = value
    return validate(result)


def portrait_bytes(value):
    from PIL import Image
    require(type(value) is str and len(value) <= 5_600_000, "Portrait PNG is too large")
    try:
        raw = base64.b64decode(value, validate=True)
        require(len(raw) <= 4 * 1024 * 1024, "Portrait PNG is too large")
        with Image.open(io.BytesIO(raw)) as image:
            require(image.format == "PNG" and 32 <= image.width <= 2048 and 32 <= image.height <= 2048,
                    "Portrait must be a 32–2048px PNG")
            image.verify()
    except (ValueError, OSError) as exc:
        raise SaveError("Invalid portrait PNG: " + str(exc)) from exc
    return raw


def empty_container():
    payload = bytearray(PROFILE_SIZE)
    payload[0x120:0x130] = b"\xff" * 16
    payload[0x134:0x137] = b"\xff" * 3
    payload[0x4d87] = 87
    return Container(bytes(64), bytes(payload))


def from_fields(fields, name, metadata=None, moveset_key=None):
    require(fields.get("has_fighter"), "Create a Story fighter in the game before making a project")
    token = uuid.uuid4().hex[:12]
    document = {"schema": SCHEMA, "identity": {"pack": "fighter-" + token, "fighter": "fighter"},
                "metadata": {"name": name, "author": "", "version": "1.0.0", "description": "", "license": "",
                             "donor": "retail/blaze"},
                "fighter": {k: copy.deepcopy(fields[k]) for k in ("stats", "styles", "caf_values", "caf_colors")}}
    if metadata:
        document["metadata"].update(metadata)
    if 1<=fields.get('combined_style',0)<=86:
        require(moveset_key is not None,'Load original fighter assets to preserve this retail moveset')
        document['fighter']['retail_moveset']=moveset_key
    return validate(document)


def from_profile(payload, name, database=None):
    """Convert fighter fields while resolving saved retail finisher identities."""
    fields=read_fields(payload);key=None
    if 1<=fields['combined_style']<=86:
        require(database is not None,'Load original fighter assets to preserve this retail moveset')
        from .movesets import Catalog
        row=Catalog(database).by_core.get(fields['combined_style'])
        require(row is not None,'Saved retail moveset is unavailable in the original catalog')
        key=row['key']
    document = from_fields(fields, name, moveset_key=key)
    values = struct.unpack_from("<4I", payload, 0x120)
    if values == (0xFFFFFFFF,) * 4:
        return document
    require(database is not None, "Load original game assets to preserve saved finisher assignments")
    require(0xFFFFFFFF not in values, "Partial saved finisher assignments are not yet supported")
    try:
        schema = database.shop.mapping(database.shop.word(12), b"SKMA")
        require(schema.get(0x47D305FD ^ 0x6FC83815) == (4, 2), "Unsupported saved finisher schema")
        identities = []
        for value in values:
            table, _, identity, offset, color = database.packed(value)
            require(table == 0x47D305FD and color == 0 and database.shop.word(offset + 16) < 82,
                    "Unsupported saved finisher assignment")
            identities.append(f"{identity:08x}")
    except (ValueError, KeyError, IndexError, struct.error) as exc:
        raise SaveError("Unsupported saved finisher assignment: " + str(exc)) from exc
    document["fighter"]["finishers"] = identities
    return validate(document)


def container(document):
    fighter = validate(document)["fighter"]
    return apply_fields(empty_container(), {k: fighter[k] for k in FIGHTER_FIELDS})


def encoded(document):
    raw = (json.dumps(validate(document), ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    require(len(raw)<=MAX_PROJECT,'Fighter project exceeds the portable file size limit')
    return raw


def read(path):
    path = Path(path)
    require(not path.is_symlink(), "Project must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_PROJECT + 1)
    require(len(raw) <= MAX_PROJECT, "Fighter project is too large")
    try:
        document = json.loads(raw, object_pairs_hook=unique,
                              parse_constant=lambda _: require(False, "Non-finite project number"))
        validate(document)
    except (ValueError, TypeError, KeyError) as exc:
        raise SaveError("Invalid fighter project: " + str(exc)) from exc
    return document, sha(raw)


def write(path, document, expected=None):
    path, raw = Path(path), encoded(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    with writer_lock(path.parent):
        require(not path.is_symlink(), "Project destination cannot be a link")
        if expected is None:
            require(not path.exists(), "Project destination already exists; use Save for the open project")
            # Exclusive creation makes Save As race-safe.
            with path.open("xb") as output:
                output.write(raw)
        else:
            require(path.is_file() and read(path)[1] == expected, "Project changed on disk; reopen it before saving")
            atomic_bytes(path, raw)
    return sha(raw)
