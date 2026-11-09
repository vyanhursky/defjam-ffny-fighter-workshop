"""Portable fighter recipes: no profile container, career, currency or source path."""
import copy
import base64
import io
import json
from pathlib import Path
import re
import uuid

from .container import Container, SaveError
from .fields import STAT_KEYS, apply_fields, combine_styles, read_fields
from .profiles import PROFILE_SIZE
from .storage import atomic_bytes, sha, writer_lock

SCHEMA = "ffny-fighter-project-1"
MAX_PROJECT = 6 * 1024 * 1024
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
    require(type(document) is dict and {"schema", "identity", "metadata", "fighter"} <= set(document)
            and set(document) <= {"schema", "identity", "metadata", "fighter", "portrait"},
            "Unsupported fighter project fields")
    require(document["schema"] == SCHEMA, "Unsupported fighter project version")
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
    require(type(fighter) is dict and set(fighter) == {"stats", "styles", "caf_values", "caf_colors"},
            "Projects contain fighter fields only")
    require(type(fighter["stats"]) is dict and set(fighter["stats"]) == set(STAT_KEYS), "Project needs all five training stats")
    require(type(fighter["styles"]) is list, "Project styles must be a list")
    combine_styles(fighter["styles"])
    # Reuse the editor's scalar/array checks without retaining any original save.
    apply_fields(empty_container(), fighter)
    require(fighter["caf_values"][0] in range(6) and fighter["caf_values"][5] in range(1, 9),
            "Unsupported fighter body or face type")
    if "portrait" in document:
        portrait_bytes(document["portrait"])
    return document


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
    payload[0x134:0x137] = b"\xff" * 3
    payload[0x4d87] = 87
    return Container(bytes(64), bytes(payload))


def from_fields(fields, name, metadata=None):
    require(fields.get("has_fighter"), "Create a Story fighter in the game before making a project")
    token = uuid.uuid4().hex[:12]
    document = {"schema": SCHEMA, "identity": {"pack": "fighter-" + token, "fighter": "fighter"},
                "metadata": {"name": name, "author": "", "version": "1.0.0", "description": "", "license": "",
                             "donor": "retail/blaze"},
                "fighter": {k: copy.deepcopy(fields[k]) for k in ("stats", "styles", "caf_values", "caf_colors")}}
    if metadata:
        document["metadata"].update(metadata)
    return validate(document)


def container(document):
    return apply_fields(empty_container(), validate(document)["fighter"])


def encoded(document):
    return (json.dumps(validate(document), ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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
