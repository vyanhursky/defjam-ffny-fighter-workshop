"""Appearance-only variants of one standalone retail-derived fighter."""

import copy
import hashlib
import uuid

from . import projects, ui_art


def rows(document):
    return [dict(id="default", name=document.get("outfit_name", "Outfit 1"))] + [
        dict(id=row["id"], name=row["name"]) for row in document.get("outfits", [])
    ]


def node(document, identity):
    return ui_art.node(document, identity)


def components(document, identity):
    selected = node(document, identity)
    return selected["definition"]["components"] if identity == "default" else selected["components"]


def view(document, identity):
    result = copy.deepcopy(document)
    selected = node(document, identity)
    if identity != "default":
        shared = result["definition"]["components"]
        for key in ("appearance", "portrait"):
            shared.pop(key, None)
        shared.update(copy.deepcopy(selected["components"]))
        result["textures"] = copy.deepcopy(selected["textures"])
        result["ui_art"] = copy.deepcopy(selected["ui_art"])
    result.pop("outfits", None)
    result.pop("outfit_name", None)
    return result


def validate(document):
    from . import retail

    name = document.get("outfit_name", "Outfit 1")
    projects.require(type(name) is str and 0 < len(name.strip()) <= 80, "Outfit name must contain 1–80 characters")
    outfits = document.get("outfits", [])
    projects.require(type(outfits) is list and len(outfits) <= 2, "A fighter supports at most three outfits")
    projects.require(
        not outfits or document.get("deployment", {}).get("mode", "add") == "add",
        "Outfit collections belong to standalone fighters",
    )
    identities = {"default", document["identity"]["fighter"]}
    used = 0
    for row in outfits:
        projects.require(
            type(row) is dict and set(row) == {"id", "name", "components", "textures", "ui_art"},
            "Invalid retail outfit fields",
        )
        identity = row["id"]
        projects.require(
            type(identity) is str and projects.SLUG.fullmatch(identity) and identity not in identities,
            "Invalid or duplicate outfit identity",
        )
        identities.add(identity)
        projects.require(
            type(row["name"]) is str and 0 < len(row["name"].strip()) <= 80, "Outfit name must contain 1–80 characters"
        )
        projects.require(
            type(row["components"]) is dict and set(row["components"]) <= {"appearance", "portrait"},
            "Outfits share their fighter's combat and performance",
        )
        retail.validate(view(document, identity))
        used += sum(len(retail.texture_bytes(v)) for v in row["textures"].values())
        used += sum(len(projects.portrait_bytes(v)) for v in row["ui_art"]["images"].values())
    ui_art.check_budget(document)
    return used


def edit(document, identity, operation, args):
    projects.require(
        document.get("deployment", {}).get("mode", "add") == "add", "Outfit collections belong to standalone fighters"
    )
    selected = node(document, identity)
    if operation == "copy":
        projects.require(len(document.get("outfits", [])) < 2, "A fighter supports at most three outfits")
        current = view(document, identity)
        identity = "outfit-" + uuid.uuid4().hex[:12]
        document.setdefault("outfits", []).append(
            dict(
                id=identity,
                name=args.get("name", "Outfit " + str(len(document["outfits"]) + 2)),
                components={
                    k: v for k, v in current["definition"]["components"].items() if k in ("appearance", "portrait")
                },
                textures=current["textures"],
                ui_art=current["ui_art"],
            )
        )
    elif operation == "rename":
        selected["outfit_name" if identity == "default" else "name"] = args["name"]
    elif operation == "remove":
        projects.require(identity != "default", "The default outfit cannot be removed")
        document["outfits"] = [r for r in document["outfits"] if r["id"] != identity]
        identity = "default"
    else:
        raise ValueError("Unknown outfit operation")
    return identity


def stage(session, root, temporary, document):
    """Compile independent fragments, then merge only appearance/portrait variants.

    Shared source assets keep their original hash-bound paths. Generated paths
    include the outfit identity; conflicting bytes are refused before export.
    """
    import json
    from pathlib import Path

    native = None
    for row in rows(document):
        identity = row["id"]
        token = hashlib.sha256(identity.encode()).hexdigest()[:12]
        fragment = Path(temporary) / ("outfit-stage-" + identity)
        fragment.mkdir()
        current = view(document, identity)
        # Each painted body has a separate resource and texture namespace, even
        # when copied outfits share the exact original model/archive assets.
        key = current["definition"]["components"].get("appearance")
        resource = next(
            (
                r
                for r in current["resources"]
                if key and not key.startswith("retail/") and key.split("/", 1)[1] == r["id"]
            ),
            None,
        )
        if resource:
            from .retail import texture_namespace

            resource["id"] = "outfit-body-" + token
            current["definition"]["components"]["appearance"] = current["identity"]["pack"] + "/" + resource["id"]
            source = resource.get("source", {})
            if "shape_names" in source:
                source["shape_names"] = texture_namespace(
                    current["identity"]["pack"], resource["id"], source["shape_names"]
                )
        part = session.stage_one(fragment, temporary, current, suffix=token, include_performance=identity == "default")
        if native is None:
            native = part
        else:
            parent = native["id"] + "/" + native["fighters"][0]["id"]
            child = part["fighters"][0]
            child.update(
                id=identity,
                name=row["name"],
                inherits=parent,
                outfit_of=parent,
                components={k: v for k, v in child["components"].items() if k in ("appearance", "portrait")},
            )
            native["fighters"].append(child)
            needed = set(child["components"].values())
            for resource in part["resources"]:
                if native["id"] + "/" + resource["id"] not in needed:
                    continue
                existing = next((r for r in native["resources"] if r["id"] == resource["id"]), None)
                projects.require(
                    existing is None or existing == resource, "Outfits have conflicting resource identities"
                )
                if existing is None:
                    native["resources"].append(resource)
        for path in fragment.rglob("*"):
            if (
                not path.is_file()
                or path.parent == fragment
                and path.name in ("fighters.json", "README.md", "LICENSE.txt")
                and identity != "default"
            ):
                continue
            target = root / path.relative_to(fragment)
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = path.read_bytes()
            projects.require(not target.exists() or target.read_bytes() == raw, "Outfit assets have conflicting paths")
            target.write_bytes(raw)
    from .retail import descriptors

    needed = {"README.md", "LICENSE.txt", "fighters.json"}
    queue = list(descriptors(native["resources"]))
    while queue:
        spec = queue.pop()
        name = spec["path"]
        if name in needed:
            continue
        needed.add(name)
        if name.endswith(".json"):
            queue.extend(descriptors(json.loads((root / name).read_bytes(), object_pairs_hook=projects.unique)))
    for path in root.rglob("*"):
        if path.is_file() and path.relative_to(root).as_posix() not in needed:
            path.unlink()
    (root / "fighters.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
    return native
