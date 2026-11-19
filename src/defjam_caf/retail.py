"""Portable retail/owned fighters using the runtime's ordinary resource contract.

The editor stages assets and donor choices; the selected runtime remains the
authority for rig, event, resource and complete native compilation acceptance.
"""

import base64
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid
import zipfile

from . import projects, ui_art, retail_outfits
from .container import SaveError

# One retail project schema; a deployment target is an optional section. Projects saved before it existed
# (project-1) open unchanged and are stamped current when validated.
SCHEMA = "ffny-retail-fighter-project-2"
EARLIER_SCHEMAS = ("ffny-retail-fighter-project-1",)
READABLE_SCHEMAS = EARLIER_SCHEMAS + (SCHEMA,)
MAX_ASSET = 64 * 1024**2
MAX_TOTAL = 64 * 1024**2
MAX_TEXTURE = 16 * 1024**2
MAX_MANIFEST_BYTES = 8 * 1024**2
KINDS = {
    "appearance": "appearance",
    "moveset": "moveset",
    "voice": "voice",
    "ai": "ai",
    "portrait": "portrait",
    "intro": "cinematic",
    "victory": "cinematic",
    "blazin": "blazin",
}


def texture_namespace(pack, resource, shapes):
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    result = {}
    for shape in shapes:
        number = int.from_bytes(hashlib.sha256((pack + "/" + resource + "/" + shape).encode()).digest()[:8], "little")
        token = ""
        for _ in range(4):
            token += alphabet[number % len(alphabet)]
            number //= len(alphabet)
        result[shape] = token
    projects.require(
        len(set(result.values())) == len(result), "Texture namespace collision; choose a different pack ID"
    )
    return result


def relative(value):
    projects.require(
        type(value) is str and value and "\\" not in value and ":" not in value,
        "Asset paths must be portable relative paths",
    )
    path = PurePosixPath(value)
    projects.require(
        not path.is_absolute() and all(p not in ("", ".", "..") for p in path.parts) and str(path) == value,
        "Asset path leaves the project",
    )
    return value


def blob(raw):
    projects.require(type(raw) is bytes and len(raw) <= MAX_ASSET, "Asset exceeds 64 MiB")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "data": base64.b64encode(raw).decode("ascii")}


def unblob(value):
    projects.require(
        type(value) is dict
        and set(value) == {"sha256", "data"}
        and type(value["data"]) is str
        and len(value["data"]) <= MAX_ASSET * 4 // 3 + 8,
        "Invalid embedded asset",
    )
    try:
        raw = base64.b64decode(value["data"], validate=True)
    except ValueError as exc:
        raise SaveError("Invalid embedded asset encoding") from exc
    projects.require(
        len(raw) <= MAX_ASSET and hashlib.sha256(raw).hexdigest() == value["sha256"], "Embedded asset hash changed"
    )
    return raw


def texture_bytes(value):
    from PIL import Image

    projects.require(type(value) is str and len(value) <= MAX_TEXTURE * 4 // 3 + 8, "Body atlas PNG exceeds 16 MiB")
    try:
        raw = base64.b64decode(value, validate=True)
        projects.require(0 < len(raw) <= MAX_TEXTURE, "Body atlas PNG exceeds 16 MiB")
        with Image.open(io.BytesIO(raw)) as image:
            projects.require(
                image.format == "PNG" and 32 <= image.width <= 2048 and 32 <= image.height <= 2048,
                "Body atlas must be a 32–2048px PNG",
            )
            image.verify()
    except (ValueError, OSError) as exc:
        raise SaveError("Invalid body atlas PNG: " + str(exc)) from exc
    return raw


def descriptors(value):
    if isinstance(value, dict):
        if {"path", "sha256"} <= set(value):
            relative(value["path"])
            projects.require(
                type(value["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", value["sha256"]), "Invalid asset digest"
            )
            yield value
        else:
            for child in value.values():
                yield from descriptors(child)
    elif isinstance(value, list):
        for child in value:
            yield from descriptors(child)


def validate(document):
    has_deployment = type(document) is dict and "deployment" in document
    has_performance = type(document) is dict and "performance" in document
    projects.require(
        type(document) is dict
        and set(document)
        == {"schema", "identity", "metadata", "definition", "resources", "assets", "ui_art", "textures"}
        | ({"deployment"} if has_deployment else set())
        | ({"performance"} if has_performance else set())
        | (set(document) & {"outfit_name", "outfits"})
        and document["schema"] in READABLE_SCHEMAS,
        "Unsupported retail fighter project fields",
    )
    if has_performance:
        from . import performance

        performance.validate(document["performance"])
        projects.require(
            not document["performance"].get("cinematics"),
            "Authored native mouth performances currently require a CAF project",
        )
        projects.require(
            not document["performance"] or document.get("deployment", {}).get("mode", "add") == "add",
            "Retail appearance workflows retain their parent's performance",
        )
    if has_deployment:
        deployment = document["deployment"]
        projects.require(
            type(deployment) is dict
            and set(deployment) == {"mode", "target"}
            and deployment["mode"] in ("add", "override", "outfit")
            and type(deployment["target"]) is str
            and re.fullmatch(r"retail/[a-z0-9]+(?:-[a-z0-9]+)*", deployment["target"]),
            "Choose a retail deployment target",
        )
        if deployment["mode"] != "add":
            projects.require(
                document["definition"]["inherits"] == deployment["target"],
                "Retail overrides/outfits retain their target combat donor",
            )
            projects.require(
                set(document["definition"]["components"]) <= {"appearance", "portrait"},
                "Retail appearance workflows retain target combat, stats and voice",
            )
    # Share identity/metadata validation without inventing a second policy.
    dummy = projects.from_fields(
        {
            "has_fighter": True,
            "stats": dict.fromkeys(("health", "upper", "lower", "speed", "toughness"), 0),
            "styles": [0],
            "caf_values": [0, 0, 0, 0, 0, 1] + [0] * 6 + [0xFFFFFFFF] * 26,
            "caf_colors": [0] * 38,
        },
        document["metadata"]["name"],
    )
    dummy.update(identity=document["identity"], metadata=document["metadata"])
    projects.validate(dummy)
    definition = document["definition"]
    projects.require(
        type(definition) is dict
        and set(definition) == {"inherits", "components"}
        and type(definition["inherits"]) is str
        and re.fullmatch("retail/[a-z0-9]+(?:-[a-z0-9]+)*", definition["inherits"]),
        "Choose a retail combat donor",
    )
    components = definition["components"]
    projects.require(
        type(components) is dict and set(components) <= set(KINDS) | {"stats", "tier"}, "Unsupported fighter component"
    )
    for key, value in components.items():
        if key == "stats":
            projects.require(
                type(value) is dict
                and set(value) <= {"health", "speed", "toughness", "charisma"}
                and all(type(v) is int and 0 <= v <= 100 for v in value.values()),
                "Retail stats must be integers from 0 to 100",
            )
        elif key == "tier":
            projects.require(type(value) is int and value in (1, 2, 4, 8), "Invalid roster tier")
        else:
            projects.require(
                type(value) is str and re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*", value),
                "Invalid component reference",
            )
    resources = document["resources"]
    projects.require(type(resources) is list and len(resources) <= 128, "Too many fighter resources")
    ids = set()
    for resource in resources:
        projects.require(
            type(resource) is dict
            and {"id", "kind", "compatibility"} <= set(resource)
            and set(resource) <= {"id", "kind", "compatibility", "source"}
            and resource["kind"] in set(KINDS.values())
            and type(resource["id"]) is str
            and projects.SLUG.fullmatch(resource["id"])
            and resource["id"] not in ids,
            "Invalid or duplicate resource",
        )
        ids.add(resource["id"])
    assets = document["assets"]
    projects.require(type(assets) is dict and len(assets) <= 4096, "Too many embedded assets")
    folded = set()
    used = 0
    for name, value in assets.items():
        relative(name)
        projects.require(name.casefold() not in folded, "Case-colliding asset paths")
        folded.add(name.casefold())
        used += len(unblob(value))
    projects.require(used <= MAX_TOTAL, "Embedded assets exceed 64 MiB")
    for spec in descriptors(resources):
        projects.require(
            spec["path"] in assets and assets[spec["path"]]["sha256"] == spec["sha256"],
            "Resource asset is missing or changed",
        )
    ui_art.validate(document["ui_art"])
    for value in document["ui_art"]["images"].values():
        used += len(projects.portrait_bytes(value))
    textures = document["textures"]
    projects.require(type(textures) is dict and len(textures) <= 64, "Invalid texture imports")
    for name, value in textures.items():
        projects.require(re.fullmatch("[A-Za-z0-9_]{4}", name) is not None, "Choose a four-character texture shape")
        used += len(texture_bytes(value))
    if "outfits" in document or "outfit_name" in document:
        used += retail_outfits.validate(document)
    projects.require(used <= MAX_TOTAL, "Combined native assets and PNG artwork exceed 64 MiB")
    document["schema"] = SCHEMA
    return document


def new(donor, name="New fighter"):
    return validate(
        {
            "schema": SCHEMA,
            "identity": {"pack": "fighter-" + uuid.uuid4().hex[:12], "fighter": "fighter"},
            "metadata": {
                "name": name,
                "author": "",
                "version": "0.1.0",
                "description": "",
                "license": "",
                "donor": donor,
            },
            "definition": {"inherits": donor, "components": {}},
            "resources": [],
            "assets": {},
            "textures": {},
            "ui_art": {"images": {}, "donor": donor, "hd_scale": 4},
        }
    )


def read_manifest(folder):
    """Bound the actual read, including the native fighter chooser's first pass."""
    with (Path(folder) / "fighters.json").open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    projects.require(len(raw) <= MAX_MANIFEST_BYTES, "Pack manifest exceeds 8 MiB")
    manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=projects.unique)
    projects.require(type(manifest) is dict, "Invalid pack manifest")
    return manifest


def import_pack(folder, fighter_id, *, manifest_override=None, include_outfits=True):
    """Read one ordinary fighter and its hash-bound transitive JSON assets."""
    folder = Path(folder).resolve()
    manifest = read_manifest(folder) if manifest_override is None else manifest_override
    projects.require(
        manifest.get("schema") == "fighter-registry-draft-1" and not manifest.get("requires"),
        "Import an independent fighter pack without dependencies",
    )
    fighter = next((f for f in manifest["fighters"] if f["id"] == fighter_id), None)
    if include_outfits and fighter:
        parent_key = fighter.get("outfit_of", "")
        if parent_key.startswith(manifest["id"] + "/"):
            fighter_id = parent_key.split("/", 1)[1]
            fighter = next((f for f in manifest["fighters"] if f["id"] == fighter_id), None)
            projects.require(fighter is not None and "outfit_of" not in fighter, "Invalid standalone outfit parent")
        children = [f for f in manifest["fighters"] if f.get("outfit_of") == manifest["id"] + "/" + fighter_id]
        if children:
            projects.require(
                len(children) <= 2 and not fighter.get("outfit_of"), "Invalid standalone outfit collection"
            )
            result = import_pack(folder, fighter_id, manifest_override=manifest, include_outfits=False)
            result["outfits"] = []
            for child in children:
                projects.require(
                    child.get("inherits") == manifest["id"] + "/" + fighter_id
                    and set(child["components"]) <= {"appearance", "portrait"},
                    "Imported outfits must inherit their parent's combat",
                )
                flattened = copy.deepcopy(manifest)
                definition = dict(fighter["components"], **child["components"])
                flattened["fighters"] = [
                    dict(id=child["id"], name=child["name"], inherits=fighter["inherits"], components=definition)
                ]
                item = import_pack(folder, child["id"], manifest_override=flattened, include_outfits=False)
                for resource in item["resources"]:
                    if not any(r["id"] == resource["id"] for r in result["resources"]):
                        result["resources"].append(resource)
                for name, value in item["assets"].items():
                    projects.require(
                        name not in result["assets"] or result["assets"][name] == value, "Conflicting outfit asset"
                    )
                    result["assets"][name] = value
                result["outfits"].append(
                    dict(
                        id=child["id"],
                        name=child["name"],
                        components={k: v for k, v in definition.items() if k in ("appearance", "portrait")},
                        textures={},
                        ui_art=copy.deepcopy(item["ui_art"]),
                    )
                )
            return validate(result)
    deployment = None
    if manifest.get("overrides"):
        rows = manifest["overrides"]
        projects.require(
            not manifest["fighters"]
            and len(rows) == 1
            and not rows[0]["supersedes"]
            and rows[0]["target"] == fighter_id
            and fighter_id.startswith("retail/"),
            "Import one independent retail appearance override at a time",
        )
        fighter = dict(
            id="override",
            name=fighter_id.split("/")[1].replace("-", " ").title(),
            inherits=fighter_id,
            components=rows[0]["components"],
        )
        deployment = dict(mode="override", target=fighter_id)
        fighter_id = "override"
    projects.require(fighter is not None, "Choose a fighter from this pack")
    projects.require(fighter.get("inherits", "").startswith("retail/"), "Imported fighter needs a retail base")
    document = new(fighter["inherits"], fighter["name"])
    document["identity"] = {"pack": manifest["id"], "fighter": fighter_id}
    if fighter.get("outfit_of"):
        deployment = dict(mode="outfit", target=fighter["outfit_of"])
    if deployment:
        document["deployment"] = deployment
    document["metadata"]["version"] = manifest["version"]
    document["definition"] = {"inherits": fighter["inherits"], "components": copy.deepcopy(fighter["components"])}
    selected = {
        v.split("/", 1)[1]
        for k, v in fighter["components"].items()
        if k in KINDS and v.startswith(manifest["id"] + "/")
    }
    document["resources"] = [copy.deepcopy(r) for r in manifest["resources"] if r["id"] in selected]
    projects.require(len(selected) == len(document["resources"]), "Fighter references a missing local resource")
    queue = list(descriptors(document["resources"]))
    used = 0
    while queue:
        spec = queue.pop()
        name = relative(spec["path"])
        if name in document["assets"]:
            projects.require(document["assets"][name]["sha256"] == spec["sha256"], "Asset has conflicting hashes")
            continue
        unresolved = folder / name
        projects.require(
            not any(p.is_symlink() for p in [unresolved, *unresolved.parents] if p != folder.parent),
            "Source assets cannot use links",
        )
        source = unresolved.resolve()
        projects.require(source.is_relative_to(folder) and source.is_file(), "Asset leaves source pack")
        projects.require(source.stat().st_size <= MAX_ASSET, "Source asset exceeds budget")
        raw = source.read_bytes()
        used += len(raw)
        projects.require(used <= MAX_TOTAL, "Imported assets exceed 64 MiB")
        projects.require(hashlib.sha256(raw).hexdigest() == spec["sha256"], "Source asset hash changed")
        document["assets"][name] = blob(raw)
        if name.endswith(".json"):
            queue.extend(descriptors(json.loads(raw, object_pairs_hook=projects.unique)))
    return validate(document)


def manifest(document):
    """Bind declared owned data to the combat donor; native compiler proves joins.

    Source geometry, transforms, graph rig hashes, samples and event metadata
    remain unchanged. A family label never bypasses actual compiler admission.
    """
    validate(document)
    result = copy.deepcopy(document)
    pack = result["identity"]["pack"]
    components = result["definition"]["components"]
    ids = {r["id"] for r in result["resources"]}
    for key, value in list(components.items()):
        if key in KINDS and value.split("/", 1)[1] in ids and not value.startswith("retail/"):
            components[key] = pack + "/" + value.split("/", 1)[1]
    family = "retail/binding-" + result["definition"]["inherits"].split("/", 1)[1]
    for resource in result["resources"]:
        for key in resource["compatibility"]:
            resource["compatibility"][key] = family
        if resource["kind"] == "appearance" and "source" in resource:
            resource["source"]["donor"] = result["definition"]["inherits"]
    return {
        "schema": "fighter-registry-draft-1",
        "id": pack,
        "version": result["metadata"]["version"],
        "requires": {},
        "resources": result["resources"],
        "fighters": [{"id": result["identity"]["fighter"], "name": result["metadata"]["name"], **result["definition"]}],
        "overrides": [],
    }


class Session:
    def __init__(self, owner):
        self.owner = owner
        self.runtime = None
        self.data = None
        self.catalog = None
        self.document = None
        self.saved = None
        self.path = None
        self.digest = None
        self.history = []
        self.draft = None
        self.active_outfit = "default"
        from .artwork_references import References

        self.artwork_references = References()

    def effective(self):
        document = copy.deepcopy(self.document)
        if document is not None and self.draft is not None:
            document["metadata"].update(copy.deepcopy(self.draft["metadata"]))
            document["identity"].update(copy.deepcopy(self.draft["identity"]))
        return document

    def api(self, arguments, temporary):
        from .fighter_mod import contract
        from . import runtimes

        runtime = runtimes.require(self.shared_runtime(), "retail", self.owner.recipe_format())["path"]
        workspace = self.owner.workspace / "retail"
        workspace.mkdir(parents=True, exist_ok=True)
        return contract(Path(runtime), arguments, temporary, workspace)

    def shared_runtime(self):
        """The game version chosen once in Game setup, unless this studio was pointed elsewhere explicitly."""
        return self.runtime or self.owner.runtime

    def game(self):
        data = self.data or self.owner.data
        projects.require(data is not None and (data / "extracted").is_dir(), "Choose the Recomp data directory first")
        return data / "extracted"

    def commit(self, document):
        validate(document)
        if document != self.document:
            self.history.append(copy.deepcopy(self.document))
            self.history = self.history[-50:]
            self.document = document
        self.draft = None
        return self.snapshot()

    def selected(self, document):
        return retail_outfits.node(document, self.active_outfit)

    def appearance_components(self, document):
        return retail_outfits.components(document, self.active_outfit)

    def selected_view(self):
        return retail_outfits.view(self.effective(), self.active_outfit)

    def snapshot(self):
        from . import performance

        rows = []
        if self.catalog:
            rows = [
                {"id": "retail/" + r["id"], "name": r["name"], "stats": r["components"]["stats"]}
                for r in self.catalog["fighters"]
            ]
        view = self.effective()
        dirty = view != self.saved
        outfits = retail_outfits.rows(view) if view is not None else []
        if not any(row["id"] == self.active_outfit for row in outfits):
            self.active_outfit = "default"
        if view is not None:
            view = retail_outfits.view(view, self.active_outfit)
        settings = performance.status(view.pop("performance", None)) if view is not None else {}
        if view is not None:
            view["asset_count"] = len(view.pop("assets"))
        data = self.data or self.owner.data
        runtime = self.shared_runtime()
        return {
            "retail": True,
            "outfits": outfits,
            "active_outfit": self.active_outfit,
            "data": str(data) if data else None,
            "runtime": str(runtime) if runtime else None,
            "setup": self.owner.setup_view(),
            "donors": rows,
            "document": view,
            "path": str(self.path) if self.path else None,
            "dirty": dirty,
            "undo": bool(self.history) or self.draft is not None,
            "roles": [{"id": r, "name": ui_art.MASTERS.get(r, r.replace("_", " "))} for r in ui_art.ROLES],
            "performance": dict(
                settings=settings,
                catalog=self.owner.performance_link.catalog if self.owner.performance_link else None,
                ai_fields=[dict(id=key, label=label) for key, label in performance.AI_FIELDS],
                project_available=bool(view and view.get("deployment", {}).get("mode", "add") == "add"),
            ),
        }

    def request(self, action, args):
        workspace = self.owner.workspace / "retail"
        workspace.mkdir(parents=True, exist_ok=True)
        if action not in ["snapshot", "draft", "configure", "new", "open", "import", "close"]:
            projects.require(self.document is not None, "Create or open a retail fighter project")
        handler = self.ACTIONS.get(action)
        if handler is None:
            raise SaveError("Unsupported retail fighter action")
        candidate = (
            None
            if action
            in [
                "snapshot",
                "draft",
                "configure",
                "new",
                "open",
                "import",
                "close",
                "undo",
                "reset",
                "save",
                "performance_connect",
                "performance_audio",
                "performance_animation",
            ]
            else self.effective()
        )
        return handler(self, action, args, workspace, candidate)

    def _request_snapshot(self, action, args, workspace, candidate=None):
        if self.catalog is None and self.shared_runtime() is not None and (self.data or self.owner.data) is not None:
            try:
                from . import runtimes

                if runtimes.describe(self.shared_runtime(), self.owner.recipe_format())["features"]["retail"]:
                    args = {"runtime": str(self.shared_runtime())}
                    action = "configure"
            except Exception:
                pass
        if action == "snapshot":
            return self.snapshot()
        return self._request_configure(action, args, workspace)

    def _request_draft(self, action, args, workspace, candidate=None):
        projects.require(
            self.document is not None
            and set(args) == {"metadata", "identity"}
            and all(type(v) is dict for v in args.values()),
            "Invalid project details draft",
        )
        projects.require(
            set(args["metadata"]) <= set(self.document["metadata"]) and set(args["identity"]) == {"pack", "fighter"},
            "Unknown project details draft fields",
        )
        self.draft = copy.deepcopy(args)
        return {"draft": True, "dirty": self.effective() != self.saved}

    def _request_configure(self, action, args, workspace, candidate=None):
        runtime = Path(args["runtime"]).resolve()
        old = self.runtime
        self.runtime = runtime
        try:
            with tempfile.TemporaryDirectory(dir=workspace) as temporary:
                self.catalog = self.api(["catalog", "--game", str(self.game())], temporary)["baseline"]
        except Exception:
            self.runtime = old
            raise
        return self.snapshot()

    def _request_performance_connect(self, action, args, workspace, candidate=None):
        from .performance_api import Link
        from . import runtimes

        runtime = runtimes.require(self.shared_runtime(), "tools", self.owner.recipe_format())["path"]
        self.owner.performance_link = Link(runtime, self.data or self.owner.data, self.owner.workspace)
        return self.snapshot()

    def _request_export_checklist(self, action, args, workspace, candidate=None):
        from . import runtimes

        document = self.effective()
        runtime = runtimes.describe(self.shared_runtime(), self.owner.recipe_format())
        checks = [
            dict(
                label="Project will be saved before export."
                if not self.path or self.effective() != self.saved
                else "Project saved.",
                status="pass",
                tab="project",
            ),
            dict(
                label="Selected game supports retail fighter export."
                if runtime and runtime["features"]["retail"]
                else "Choose a game version with retail fighter export.",
                status="pass" if runtime and runtime["features"]["retail"] else "fail",
                tab="setup",
            ),
        ]
        if document.get("performance") and not (runtime and runtime["features"]["tools"]):
            checks.append(
                dict(
                    label="Performance export needs compatible voice, AI and animation tools.",
                    status="fail",
                    tab="setup",
                )
            )
        if document.get("outfits"):
            supported = bool(runtime and "standalone-retail-outfits-1" in runtime.get("extensions", []))
            checks.append(
                dict(
                    label="All outfits will share one fighter and combat settings."
                    if supported
                    else "Multiple outfits need a game version with standalone outfit support in Game setup.",
                    status="pass" if supported else "fail",
                    tab="setup",
                )
            )
        try:
            validate(document)
            checks.append(dict(label="Project details and imported assets are valid.", status="pass", tab="project"))
        except SaveError as error:
            checks.append(dict(label=str(error), status="fail", tab="project"))
        checks.append(
            dict(
                label="Imported body is included."
                if document["definition"]["components"].get("appearance")
                else "Body inherits the original donor.",
                status="note",
                tab="appearance",
            )
        )
        checks.append(
            dict(
                label="Imported menu art is included."
                if document["ui_art"]["images"]
                else "Menu artwork uses donor fallbacks.",
                status="note",
                tab="textures",
            )
        )
        return dict(checks=checks, can_export=all(row["status"] != "fail" for row in checks))

    def _request_performance_audio(self, action, args, workspace, candidate=None):
        from . import performance

        link = self.owner.performance_link
        projects.require(link is not None, "Connect compatible fighter tools first")
        if action == "performance_animation":
            if args.get("operation") == "list":
                return link.animation(args)
            from . import runtimes

            projects.require(
                "retail-animation-preview-1"
                in runtimes.inspect(self.shared_runtime(), self.owner.recipe_format())["extensions"],
                "This game version cannot preview retail animation. Choose a compatible version in Game setup.",
            )
            with tempfile.TemporaryDirectory(prefix="animation-", dir=workspace) as temporary:
                root = Path(temporary) / self.document["identity"]["pack"]
                root.mkdir()
                self.stage(root, temporary, include_performance=False)
                request = Path(temporary) / "animation.json"
                request.write_text(json.dumps(args), encoding="utf-8")
                return self.api(
                    [
                        "workshop-animation",
                        "--game",
                        str(self.game()),
                        "--pack",
                        str(root),
                        "--workshop-request",
                        str(request),
                    ],
                    temporary,
                )
        if args.get("override"):
            encoded = self.effective().get("performance", {}).get("voice", {}).get("clips", {}).get(args["override"])
            projects.require(encoded is not None, "No imported clip in this slot")
            performance.audio_bytes(encoded)
            return dict(mime="audio/wav", data=encoded)
        return link.voice(args)

    def _request_performance_set(self, action, args, workspace, candidate=None):
        from . import performance

        projects.require(
            candidate.get("deployment", {}).get("mode", "add") == "add",
            "Retail appearance workflows retain their parent's performance",
        )
        candidate["performance"] = performance.edited(
            candidate.get("performance"), action.removeprefix("performance_"), args, self.owner.performance_link
        )
        return self.commit(candidate)

    def _request_moveset(self, action, args, workspace, candidate=None):
        projects.require(
            candidate.get("deployment", {}).get("mode", "add") == "add",
            "Retail appearance workflows retain their parent's combat",
        )
        projects.require(
            self.catalog and any("retail/" + row["id"] == args["donor"] for row in self.catalog["fighters"]),
            "Unknown moveset donor",
        )
        inherited = candidate["definition"]["inherits"]
        baseline = next(row for row in self.catalog["fighters"] if "retail/" + row["id"] == inherited)
        candidate["definition"]["components"].setdefault("stats", copy.deepcopy(baseline["components"]["stats"]))
        candidate["definition"]["inherits"] = args["donor"]
        candidate["definition"]["components"].pop("moveset", None)
        # Explicit performance settings and appearance assets remain intact.
        # The compiler still proves the new motion family's rig compatibility.
        return self.commit(candidate)

    def _request_new(self, action, args, workspace, candidate=None):
        if action == "new":
            document = new(args["donor"])
        elif action == "open":
            document, digest = projects.read(args["path"])
            projects.require(document["schema"] in READABLE_SCHEMAS, "Open CAF projects in the CAF editor")
        else:
            document = import_pack(args["folder"], args["fighter"])
        self.document = document
        self.saved = copy.deepcopy(document) if action == "open" else None
        self.path = Path(args["path"]) if action == "open" else None
        self.digest = digest if action == "open" else None
        self.history = []
        self.draft = None
        self.active_outfit = "default"
        if action == "new" and args.get("mode", "add") != "add":
            self.document["deployment"] = dict(mode=args["mode"], target=args["donor"])
            validate(self.document)
        return self.snapshot()

    def _request_close(self, action, args, workspace, candidate=None):
        self.document = self.saved = self.path = self.digest = self.draft = None
        self.history = []
        return self.snapshot()

    def _request_undo(self, action, args, workspace, candidate=None):
        if self.draft is not None:
            self.draft = None
        elif self.history:
            self.document = self.history.pop()
        return self.snapshot()

    def _request_reset(self, action, args, workspace, candidate=None):
        projects.require(self.saved is not None, "Save this new project before resetting it")
        self.document = copy.deepcopy(self.saved)
        self.history = []
        self.draft = None
        return self.snapshot()

    def _request_save(self, action, args, workspace, candidate=None):
        target = Path(args["path"]) if args.get("path") else self.path
        projects.require(target is not None, "Choose a project destination")
        expected = self.digest if self.path == target else None
        document = validate(self.effective())
        self.digest = projects.write(target, document, expected)
        self.document = document
        self.draft = None
        self.path = target
        self.saved = copy.deepcopy(document)
        self.history = []
        return self.snapshot()

    def _request_deployment(self, action, args, workspace, candidate=None):
        projects.require(
            self.catalog and any("retail/" + r["id"] == args["target"] for r in self.catalog["fighters"]),
            "Unknown retail target",
        )
        candidate["deployment"] = dict(mode=args["mode"], target=args["target"])
        if args["mode"] != "add":
            candidate["definition"]["inherits"] = args["target"]
        return self.commit(candidate)

    def _request_details(self, action, args, workspace, candidate=None):
        candidate["metadata"].update(args["metadata"])
        candidate["identity"].update(args["identity"])
        return self.commit(candidate)

    def _request_combat(self, action, args, workspace, candidate=None):
        projects.require(
            self.catalog and any("retail/" + r["id"] == args["donor"] for r in self.catalog["fighters"]),
            "Unknown combat donor",
        )
        candidate["definition"]["inherits"] = args["donor"]
        candidate["definition"]["components"].pop("moveset", None)
        candidate["definition"]["components"].pop("stats", None)
        return self.commit(candidate)

    def _request_component(self, action, args, workspace, candidate=None):
        key = args["component"]
        projects.require(key in KINDS, "Unknown fighter component")
        components = (
            self.appearance_components(candidate)
            if key in ("appearance", "portrait")
            else candidate["definition"]["components"]
        )
        if args.get("resource"):
            components[key] = args["resource"]
        else:
            components.pop(key, None)
        return self.commit(candidate)

    def _request_outfit(self, action, args, workspace, candidate=None):
        if action == "outfit_select":
            retail_outfits.node(candidate, args["id"])
            self.active_outfit = args["id"]
            return self.snapshot()
        identity = retail_outfits.edit(candidate, self.active_outfit, action.removeprefix("outfit_"), args)
        validate(candidate)
        self.active_outfit = identity
        return self.commit(candidate)

    def _request_stats(self, action, args, workspace, candidate=None):
        candidate["definition"]["components"]["stats"] = args["stats"]
        return self.commit(candidate)

    def _request_ui(self, action, args, workspace, candidate=None):
        document = candidate
        candidate = self.selected(candidate)
        role = args["role"]
        projects.require(role in ui_art.ROLES, "Unknown artwork role")
        if args.get("png"):
            projects.portrait_bytes(args["png"])
            if role in ui_art.MASTERS:
                covered = {role} | ({"grid_normal", "grid_selected"} if role == "icon" else set())
                for key in list(candidate["ui_art"]["images"]):
                    if ui_art.master(key) in covered:
                        candidate["ui_art"]["images"].pop(key)
            candidate["ui_art"]["images"][role] = args["png"]
        else:
            candidate["ui_art"]["images"].pop(role, None)
        return self.commit(document)

    def _request_artwork_stage(self, action, args, workspace, candidate=None):
        document = self.selected_view()
        self.owner.progress("Loading original artwork for all layouts…")
        return self.artwork_references.stage(
            self.shared_runtime(),
            self.game(),
            document["ui_art"].get("donor", document["metadata"]["donor"]),
            workspace,
            self.owner.recipe_format(),
        )

    def _request_ui_settings(self, action, args, workspace, candidate=None):
        self.selected(candidate)["ui_art"].update(donor=args["donor"], hd_scale=args["hd_scale"])
        return self.commit(candidate)

    def _request_texture(self, action, args, workspace, candidate=None):
        document = candidate
        candidate = self.selected(candidate)
        if args.get("png"):
            candidate["textures"][args["shape"]] = args["png"]
        else:
            candidate["textures"].pop(args["shape"], None)
        return self.commit(document)

    def _request_preview(self, action, args, workspace, candidate=None):
        with tempfile.TemporaryDirectory(prefix="retail-", dir=workspace) as temporary:
            root = Path(temporary) / self.document["identity"]["pack"]
            root.mkdir()
            if action == "appearance":
                resource_id = "retail-body-" + uuid.uuid4().hex[:12]
                output = Path(temporary) / "appearance"
                report = self.api(
                    [
                        "export-retail-appearance",
                        "--game",
                        str(self.game()),
                        "--donor",
                        args["donor"],
                        "--portrait-out",
                        str(output),
                    ],
                    temporary,
                )
                resource = {
                    "id": resource_id,
                    "kind": "appearance",
                    "compatibility": {"skeleton": "retail/binding-" + args["donor"].split("/")[1]},
                    "source": report["source"],
                }
                resource["source"].update(
                    format="eagl-appearance-2",
                    shape_names=texture_namespace(candidate["identity"]["pack"], resource_id, report["shapes"]),
                )
                for spec in descriptors(resource):
                    raw = (output / spec["path"]).read_bytes()
                    spec["path"] = resource_id + "/" + spec["path"]
                    candidate["assets"][spec["path"]] = blob(raw)
                candidate["resources"].append(resource)
                self.appearance_components(candidate)["appearance"] = candidate["identity"]["pack"] + "/" + resource_id
                self.selected(candidate)["textures"] = {}
                self.prune_appearance_assets(candidate)
                return self.commit(candidate)
            self.stage(root, temporary, include_performance=action != "preview", collection=action != "preview")
            if action == "preview":
                report = self.api(["preview-fighter", "--game", str(self.game()), "--pack", str(root)], temporary)
                return report["preview"]
            report = self.api(["validate", "--pack", str(root), "--game", str(self.game())], temporary)
            projects.require(report.get("native_compilation") is True, "Runtime did not confirm native compilation")
            destination = Path(args["path"])
            projects.require(not destination.exists(), "ZIP destination already exists")
            destination.parent.mkdir(parents=True, exist_ok=True)
            created = False
            try:
                with destination.open("xb") as output:
                    created = True
                    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        for path in sorted(root.rglob("*")):
                            if path.is_file():
                                archive.write(path, root.name + "/" + path.relative_to(root).as_posix())
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
            return {
                "snapshot": self.snapshot(),
                "message": "Validated retail fighter exported to " + str(destination),
                "report": report,
            }

    ACTIONS = {
        "snapshot": _request_snapshot,
        "draft": _request_draft,
        "configure": _request_configure,
        "new": _request_new,
        "open": _request_new,
        "import": _request_new,
        "close": _request_close,
        "undo": _request_undo,
        "reset": _request_reset,
        "save": _request_save,
        "deployment": _request_deployment,
        "details": _request_details,
        "combat": _request_combat,
        "moveset": _request_moveset,
        "performance_connect": _request_performance_connect,
        "export_checklist": _request_export_checklist,
        "performance_audio": _request_performance_audio,
        "performance_animation": _request_performance_audio,
        "performance_set": _request_performance_set,
        "performance_clear": _request_performance_set,
        "performance_clip": _request_performance_set,
        "component": _request_component,
        "outfit_select": _request_outfit,
        "outfit_copy": _request_outfit,
        "outfit_rename": _request_outfit,
        "outfit_remove": _request_outfit,
        "stats": _request_stats,
        "ui": _request_ui,
        "artwork_stage": _request_artwork_stage,
        "ui_settings": _request_ui_settings,
        "texture": _request_texture,
        "preview": _request_preview,
        "appearance": _request_preview,
        "export": _request_preview,
    }

    def prune_appearance_assets(self, document):
        used = {v for k, v in document["definition"]["components"].items() if k in KINDS}
        for row in document.get("outfits", []):
            used.update(row["components"].values())
        ids = {v.split("/", 1)[1] for v in used if not v.startswith("retail/")}
        document["resources"] = [r for r in document["resources"] if r["kind"] != "appearance" or r["id"] in ids]
        needed = set()
        queue = list(descriptors(document["resources"]))
        while queue:
            spec = queue.pop()
            name = spec["path"]
            if name in needed:
                continue
            needed.add(name)
            if name.endswith(".json"):
                queue.extend(
                    descriptors(json.loads(unblob(document["assets"][name]), object_pairs_hook=projects.unique))
                )
        document["assets"] = {k: v for k, v in document["assets"].items() if k in needed}

    def stage(self, root, temporary, *, include_performance=True, collection=False):
        document = self.effective()
        if collection and document.get("outfits"):
            from . import runtimes

            projects.require(
                "standalone-retail-outfits-1"
                in runtimes.inspect(self.shared_runtime(), self.owner.recipe_format())["extensions"],
                "Multiple outfits need a game version with standalone outfit support in Game setup.",
            )
            return retail_outfits.stage(self, root, temporary, document)
        return self.stage_one(root, temporary, self.selected_view(), include_performance=include_performance)

    def stage_one(self, root, temporary, document, *, include_performance=True, suffix=""):
        native = manifest(document)
        for name, value in document["assets"].items():
            path = root / relative(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(unblob(value))
        if document["textures"]:
            spec = {
                name: {
                    "path": "texture-imports/" + (suffix + "/" if suffix else "") + name + ".png",
                    "sha256": hashlib.sha256(texture_bytes(value)).hexdigest(),
                }
                for name, value in document["textures"].items()
            }
            for name, value in document["textures"].items():
                path = root / spec[name]["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(texture_bytes(value))
            # Typed texture sources are compiled by the runtime, never renamed PNGs.
            key = native["fighters"][0]["components"].get("appearance")
            resource = next((r for r in native["resources"] if key == native["id"] + "/" + r["id"]), None)
            projects.require(resource is not None, "Import a native appearance before painting its textures")
            mapping = dict(resource["source"].get("shape_names", {}))
            mapping.update(
                texture_namespace(native["id"], resource["id"], [shape for shape in spec if shape not in mapping])
            )
            resource["source"] = {
                **resource["source"],
                "format": "eagl-appearance-png-1",
                "images": spec,
                "shape_names": mapping,
            }
        art = document["ui_art"]
        if art["images"]:
            source = {
                "format": "eagl-portrait-png-1",
                "donor": art.get("donor", document["metadata"]["donor"]),
                "hd_scale": art.get("hd_scale", 4),
                "images": {},
            }
            for role, value in art["images"].items():
                raw = projects.portrait_bytes(value)
                name = "ui-art/" + hashlib.sha256(raw).hexdigest() + ".png"
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                source["images"][role] = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
            resource_id = "workshop-ui" + ("-" + suffix if suffix else "")
            native["resources"] = [r for r in native["resources"] if r["id"] != resource_id]
            native["resources"].append({"id": resource_id, "kind": "portrait", "compatibility": {}, "source": source})
            native["fighters"][0]["components"]["portrait"] = native["id"] + "/" + resource_id
        if include_performance and document.get("performance"):
            from .performance_exports import export_settings

            generated = export_settings(
                self.shared_runtime(),
                self.game(),
                self.owner.workspace / "retail",
                temporary,
                root,
                document["identity"]["pack"],
                document["definition"]["inherits"],
                document["performance"],
            )
            identifiers = {row["id"] for row in generated["resources"]}
            native["resources"] = [row for row in native["resources"] if row["id"] not in identifiers] + generated[
                "resources"
            ]
            native["fighters"][0]["components"].update(generated["components"])
        selected = {v for k, v in native["fighters"][0]["components"].items() if k in KINDS}
        native["resources"] = [r for r in native["resources"] if native["id"] + "/" + r["id"] in selected]
        deployment = document.get("deployment", dict(mode="add", target=document["definition"]["inherits"]))
        if deployment["mode"] == "override":
            projects.require(
                set(native["fighters"][0]["components"]) <= {"appearance"},
                "Retail override currently supports appearance only; clear UI overrides",
            )
            projects.require(native["fighters"][0]["components"], "Import an appearance before exporting an override")
            native["overrides"] = [
                dict(target=deployment["target"], components=native["fighters"][0]["components"], supersedes=[])
            ]
            native["fighters"] = []
        elif deployment["mode"] == "outfit":
            native["fighters"][0]["outfit_of"] = deployment["target"]
        # Keep only transitively declared assets; unused imported resources must
        # not leak original art into the export or violate ordinary inventory.
        needed = set()
        queue = list(descriptors(native["resources"]))
        while queue:
            spec = queue.pop()
            name = spec["path"]
            if name in needed:
                continue
            needed.add(name)
            path = root / name
            projects.require(path.is_file(), "Declared asset is unavailable")
            if name.endswith(".json"):
                queue.extend(descriptors(json.loads(path.read_bytes(), object_pairs_hook=projects.unique)))
        for path in root.rglob("*"):
            if path.is_file() and path.relative_to(root).as_posix() not in needed:
                path.unlink()
        (root / "fighters.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
        (root / "README.md").write_text(
            "# "
            + document["metadata"]["name"]
            + "\n\n"
            + document["metadata"]["description"]
            + "\n\nAuthor: "
            + document["metadata"]["author"]
            + "\nNative compilation is separate from gameplay acceptance.\n",
            encoding="utf-8",
        )
        (root / "LICENSE.txt").write_text(
            document["metadata"]["license"]
            or "Original and supplied artwork remains outside the source-code license.\n",
            encoding="utf-8",
        )
        return native
