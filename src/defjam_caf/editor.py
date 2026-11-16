"""Desktop-independent editor session; all mutations are explicit actions."""

import copy
import hashlib
import json
from pathlib import Path

from .appearance import Appearance
from .assets import build_cache, Database
from . import blazin
from .container import SaveError
from .fields import apply_fields, read_fields, STYLE_NAMES, CASH_LIMIT, DEV_LIMIT
from .profiles import discover
from .storage import save_profile, export_profile, duplicate, read_archive, install_files
from . import projects, outfits, ui_art, backups, runtimes, remembered
from . import __version__
from .contracts import FighterProject, Snapshot


RETAIL_MOVESET_NOTICE = (
    "This writes an original fighter's moveset into your real Story save. Only game builds with the Story "
    "retail-moveset adapter understand it; builds without it, including Recomp v1.1.1 and v1.2.0-beta.1, have not "
    "been tested with such a save. A backup is made first. Change the moveset back to a CAF combination to undo it."
)


class Editor:
    project: FighterProject | None

    def group_label(self, slot):
        if slot == 25:
            return "Earrings (pair)"
        if slot >= 29:
            return (
                "Tattoo - "
                + (
                    "Head & Neck",
                    "Chest & Stomach",
                    "Back",
                    "Left Arm",
                    "Left Forearm",
                    "Right Arm",
                    "Right Forearm",
                    "Left Leg",
                    "Right Leg",
                )[slot - 29]
            )
        return self.cache.groups[str(slot)]["label"]

    def __init__(self, workspace, progress=lambda message: None):
        self.workspace = Path(workspace)
        self.progress = progress
        self.data = None
        self.discovery = None
        self.profile = None
        self.edits = {}
        self.history = []
        self.cache = None
        self.appearance = None
        self.blazin = None
        self.blazin_error = "Load original game assets to choose Blazin' moves."
        self.movesets = None
        self.moveset_error = "Load original game assets to choose a retail moveset."
        self.preview_error = None
        self.preview_detail = None
        self._face_preview_basis = {}
        self.performance_link = None
        self.last_export = None
        self.runtime = remembered.recall(self.workspace, "runtime")
        self.project = None
        self.project_path = self.project_hash = None
        self.project_origin = None
        self._clear_drafts()
        self.active_outfit = outfits.DEFAULT
        self._project_base_document = self._project_base = None
        from .retail import Session

        self.retail = Session(self)

    def base(self):
        if self.project is not None:
            source = self.outfit_draft if self.outfit_draft is not None else self.project
            fighter = source["fighter"]
            appearance = (
                fighter
                if self.active_outfit == outfits.DEFAULT
                else next(row for row in source["outfits"] if row["id"] == self.active_outfit)
            )
            key = (
                tuple(sorted(fighter["stats"].items())),
                tuple(fighter["styles"]),
                tuple(appearance["caf_values"]),
                tuple(appearance["caf_colors"]),
            )
            if self._project_base_document != key:
                view = outfits.view(source, self.active_outfit)
                self._project_base = apply_fields(
                    projects.empty_container(), {k: view["fighter"][k] for k in projects.FIGHTER_FIELDS}
                )
                self._project_base_document = key
            return self._project_base
        if self.profile is None:
            raise SaveError("Choose a profile or open a fighter project first")
        return self.profile.container

    def project_source(self):
        return self.outfit_draft if self.outfit_draft is not None else self.project

    def active_view(self):
        return outfits.view(self.project_source(), self.active_outfit) if self.project is not None else None

    def remember(self):
        self.history.append(
            copy.deepcopy(
                dict(
                    edits=self.edits,
                    active_outfit=self.active_outfit,
                    outfit_draft=self.outfit_draft,
                    portrait_edit=self.portrait_edit,
                    texture_edit=self.texture_edit,
                    metadata_edit=self.metadata_edit,
                )
            )
        )
        self.history = self.history[-100:]

    def flush_outfit(self):
        document = self.project_document(validate=False)
        self.outfit_draft = None if document == self.project else document
        self.edits = {}
        self.portrait_edit = self.texture_edit = self.metadata_edit = None

    def project_document(self, validate=True):
        source = self.project_source()
        document = outfits.view(source, self.active_outfit)
        if self.metadata_edit is not None:
            document.update(copy.deepcopy(self.metadata_edit))
        fields = read_fields(self.current().payload)
        document["fighter"].update({k: copy.deepcopy(fields[k]) for k in projects.FIGHTER_FIELDS})
        if "finishers" in self.edits:
            if self.edits["finishers"] is None:
                document["fighter"].pop("finishers", None)
            else:
                document["fighter"]["finishers"] = self.edits["finishers"][:]
        if self.portrait_edit is not None:
            document["portrait"] = self.portrait_edit
        if self.texture_edit is not None:
            document["textures"] = copy.deepcopy(self.texture_edit)
        if "textures" in document:
            # Imported RGB remains the author's override across appearance
            # changes. Rebind the same bytes to the newly staged outfit.
            document["textures"]["appearance_sha256"] = projects.appearance_hash(document["fighter"])
        document = outfits.replace_view(source, self.active_outfit, document)
        return projects.validate(document) if validate else document

    def create_project(self, path):
        if self.profile is not None:
            self.project_origin = self.profile.name
        fields = read_fields(self.current().payload)
        document = (
            projects.from_profile(
                self.current().payload,
                self.profile.name,
                self.blazin.database if self.blazin else self.cache.db if self.cache else None,
            )
            if self.profile
            else projects.from_fields(fields, self.project["metadata"]["name"])
        )
        if self.project is not None:
            source = self.project_document()
            identity = document["identity"]
            document = copy.deepcopy(source)
            document["identity"] = identity
        digest = projects.write(path, document)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.profile = None
        self._clear_drafts()
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_project(self, path):
        self.project_origin = None
        document, digest = projects.read(path)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.active_outfit = outfits.DEFAULT
        self.outfit_draft = None
        self.profile = None
        self.portrait_edit = self.metadata_edit = None
        self.texture_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_data(self, data):
        self.performance_link = None
        data = Path(data).expanduser().resolve()
        result = discover(data)
        self.data, self.discovery = data, result
        self.cache = self.appearance = None
        self.movesets = None
        self.moveset_error = "Load original game assets to choose a retail moveset."
        self.blazin = None
        self.blazin_error = "Load original game assets to choose Blazin' moves."
        self.preview_error = None
        self.preview_detail = None
        if (data / "extracted").is_dir():
            try:
                self.cache = build_cache(data / "extracted", self.workspace, self.progress)
                self.appearance = Appearance(self.cache)
            except (OSError, ValueError, KeyError) as exc:
                from .diagnostics import log_detail

                self.preview_error = "The 3D wardrobe could not be prepared. Check Game setup."
                self.preview_detail = str(exc)
                log_detail(self.workspace, "CAF cache could not be loaded: " + str(exc))
        else:
            self.preview_error = "Choose the Recomp data directory containing extracted game assets for the 3D preview."
        if (data / "extracted").is_dir():
            try:
                self.blazin = blazin.Catalog(self.cache.db if self.cache else Database(data / "extracted"))
                self.blazin_error = None
            except (OSError, ValueError, KeyError, SaveError) as exc:
                self.blazin_error = "Blazin' catalog could not be loaded: " + str(exc)
            try:
                from .movesets import Catalog

                self.movesets = Catalog(self.cache.db if self.cache else Database(data / "extracted"))
                self.moveset_error = None
            except (OSError, ValueError, KeyError, SaveError) as exc:
                self.moveset_error = "Retail moveset catalog could not be loaded: " + str(exc)
        candidates = [p for p in result.profiles if read_fields(p.container.payload)["has_fighter"]]
        chosen = max(candidates or result.profiles, key=lambda p: p.path.stat().st_mtime, default=None)
        if self.project is not None:
            return self.snapshot()
        if chosen:
            self.select_profile(chosen.name)
        else:
            self.profile = None
            self.edits, self.history = {}, []
        return self.snapshot()

    def recipe_format(self):
        from .fighter_mod import RECIPE_FORMAT

        return RECIPE_FORMAT

    def setup_view(self):
        """What the Game setup dialog and the header chip show: the data folder and the chosen game version."""
        runtime = runtimes.describe(self.runtime, self.recipe_format()) if self.runtime else None
        folder = remembered.recall(self.workspace, "app") or runtimes.default_folder()
        data = self.data or remembered.recall(self.workspace, "data")
        from . import cache_maintenance

        return dict(
            data=str(data) if data else None,
            runtime=runtime,
            folder=str(folder) if folder else None,
            workspace=str(self.workspace.resolve()),
            cache=cache_maintenance.info(self.workspace),
            version=__version__,
            ready=bool(data and runtime and runtime["usable"]),
        )

    def close_project(self):
        """Leave the open fighter project so a workflow can start clean. Story profiles reload from the data folder."""
        self.project = self.project_path = self.project_hash = None
        self.project_origin = None
        self.active_outfit = outfits.DEFAULT
        self._clear_drafts()
        self.edits, self.history = {}, []
        return self.open_data(self.data) if self.data else self.snapshot()

    def need_runtime(self, args, feature):
        """The runtime an action should use: an explicit one (tests, scripts) or the one chosen in Game setup."""
        runtime = args.get("runtime") or self.runtime
        runtimes.require(runtime, feature, self.recipe_format())
        return Path(runtime)

    def export_summary(self, path, report):
        """What the player needs after an export: where it is, what was checked, and what it needs to run."""
        import hashlib
        from .fighter_mod import RECIPE_FORMAT

        document = self.project_document()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        count = len(outfits.entries(document))
        lines = [
            "Saved to " + str(path),
            f"{path.stat().st_size / 1048576:.1f} MiB · SHA-256 {digest.hexdigest()[:16]}…",
            (
                "Checked against your game files: the whole pack compiled natively."
                if report.get("native_compilation")
                else "The runtime did not report a native compile."
            ),
            f"{count} outfit{'' if count == 1 else 's'} in this fighter.",
            "Needs a game build that supports " + RECIPE_FORMAT + ".",
            "To play it: in the launcher, open Mods > Fighters, add this ZIP and enable the pack.",
        ]
        return dict(title="Fighter mod exported", folder="export", lines=lines)

    def select_profile(self, name):
        self.discovery = discover(self.data)
        self.profile = next((p for p in self.discovery.profiles if p.name == name), None)
        if self.profile is None:
            raise SaveError("Profile is unavailable; refresh the data directory")
        self.project = self.project_path = self.project_hash = None
        self.outfit_draft = None
        self.active_outfit = outfits.DEFAULT
        self.portrait_edit = self.metadata_edit = None
        self.texture_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def current(self):
        return apply_fields(self.base(), {k: v for k, v in self.edits.items() if k != "finishers"})

    def blazin_keys(self, edits=None):
        edits = self.edits if edits is None else edits
        if self.project is not None:
            return blazin.project_keys(edits.get("finishers", self.project_source()["fighter"].get("finishers")))
        if self.blazin and self.profile:
            return self.blazin.profile_keys(apply_fields(self.base(), edits).payload)
        return [None] * 4

    def retail_moveset_save(self) -> str | None:
        """The notice a Story save needs acknowledged, or None.

        A retail moveset core (1..86) in a real Story save is only understood by game builds that carry the Story
        retail-moveset adapter. Older builds have not been tested with such a save, so the player must say they
        know before the save is written. The check lives here, not in the page, so no front end can skip it."""
        if self.profile is None or self.project is not None:
            return None
        before, after = (
            read_fields(self.base().payload)["combined_style"],
            read_fields(self.current().payload)["combined_style"],
        )
        if before == after or not 1 <= after <= 86:
            return None
        return RETAIL_MOVESET_NOTICE

    def stage(self, changes):
        if "moveset_core" in changes and (
            self.project is not None or not self.movesets or changes["moveset_core"] not in self.movesets.by_core
        ):
            raise SaveError("Choose a retail moveset through the loaded catalog")
        if self.project is not None and set(changes) & {"cash", "development"}:
            raise SaveError("Fighter projects have no Story currency")
        if not read_fields(self.current().payload)["has_fighter"]:
            raise SaveError("This profile has no Story fighter. Create one in the game first")
        if "blazin_values" in changes:
            if self.project is not None or not self.blazin:
                raise SaveError("Choose Blazin' moves through the loaded catalog")
            self.blazin.validate_values(changes["blazin_values"])
        if "finishers" in changes:
            if self.project is None or not self.blazin:
                raise SaveError("Choose project Blazin' moves through the loaded catalog")
            if changes["finishers"] is not None:
                self.blazin.select(blazin.project_keys(changes["finishers"]))
        combined = copy.deepcopy(self.edits)
        if "styles" in changes:
            combined.pop("moveset_core", None)
        if "stats" in changes:
            combined["stats"] = dict(combined.get("stats", {}), **changes["stats"])
        combined.update({k: v for k, v in changes.items() if k != "stats"})
        candidate = apply_fields(self.base(), {k: v for k, v in combined.items() if k != "finishers"})
        if candidate.payload == self.current().payload and self.blazin_keys(combined) == self.blazin_keys():
            return self.snapshot()
        self.remember()
        self.edits = combined
        return self.snapshot()

    def stage_appearance(self, changes):
        if self.appearance is None:
            raise SaveError("Load the original game assets before changing appearance")
        fields = read_fields(self.current().payload)
        edited = self.appearance.change(fields, changes)
        from .face_geometry import basis

        if (self.active_view() or {}).get("face_sculpt") and basis(fields) != basis(dict(fields, **edited)):
            raise SaveError("Clear the face sculpt before changing its body or facial geometry presets")
        # Validate a complete source outfit before any bytes can be staged.
        try:
            self.cache.compose(self.appearance.outfit(dict(fields, **edited)))
        except KeyError as exc:
            raise SaveError(
                "This item combination cannot be previewed yet; the existing appearance was preserved"
            ) from exc
        return self.stage(edited)

    def changes(self):
        if self.profile is None and self.project is None:
            return []
        if self.project is not None and (
            self.outfit_draft is not None or {"outfits", "outfit_name"} & set(self.project)
        ):
            return self.outfit_changes()
        before, after = read_fields(self.base().payload), read_fields(self.current().payload)
        result = []
        if self.metadata_edit is not None:
            result.append("Project details changed")
        if self.portrait_edit is not None:
            result.append("Project portrait changed")
        if self.texture_edit is not None:
            result.append("Project texture atlases changed")
        for key, label in (("cash", "Cash"), ("development", "Development points")):
            if before[key] != after[key]:
                result.append(f"{label}: {before[key]:,} → {after[key]:,}")
        for key in before["stats"]:
            if before["stats"][key] != after["stats"][key]:
                result.append(f"{key.capitalize()}: {before['stats'][key]} → {after['stats'][key]}")
        if before["styles"] != after["styles"]:
            result.append("Fighting styles: " + ", ".join(STYLE_NAMES[i] for i in after["styles"]))
        before_moves = self.blazin_keys({})
        if before["combined_style"] != after["combined_style"]:
            core = after["combined_style"]
            row = self.movesets.by_core.get(core) if self.movesets else None
            result.append("Moveset: " + (row["label"] if row else "CAF combination"))
            if self.retail_moveset_save():
                result.append(
                    "This save will need a game build with retail-moveset support (see the warning before saving)"
                )
        for slot, (old, new) in enumerate(zip(before_moves, self.blazin_keys(), strict=False)):
            if old != new:
                result.append(f"Blazin' slot {slot + 1}: " + (self.blazin.label(new) if self.blazin else str(new)))
        for slot, (old, new, oc, nc) in enumerate(
            zip(before["caf_values"], after["caf_values"], before["caf_colors"], after["caf_colors"], strict=False)
        ):
            if old != new or oc != nc:
                label = {0: "Body build", 1: "Skin tone"}.get(slot)
                if not label and self.cache:
                    label = self.group_label(slot)
                result.append((label or "Appearance") + " changed")
        return result

    def outfit_changes(self):
        before, after = self.project, self.project_document(validate=False)
        result = []
        for key, label in (
            ("voice", "Voice"),
            ("intro", "Entrance sequence"),
            ("victory", "Victory sequence"),
            ("ai", "AI personality"),
        ):
            if before.get("performance", {}).get(key) != after.get("performance", {}).get(key):
                result.append(label + " changed (all outfits)")
        if any(before[k] != after[k] for k in ("identity", "metadata")):
            result.append("Project details changed")
        for key, label in (
            ("stats", "Training stats"),
            ("styles", "Fighting styles"),
            ("finishers", "Blazin' assignments"),
            ("retail_moveset", "Moveset selection"),
        ):
            if before["fighter"].get(key) != after["fighter"].get(key):
                result.append(label + " changed (all outfits)")
        old, new = ({row["id"]: row["name"] for row in outfits.entries(doc)} for doc in (before, after))
        for identity in old.keys() - new.keys():
            result.append("Outfit removed: " + old[identity])
        for identity, name in new.items():
            if identity not in old:
                result.append("Outfit added: " + name)
                continue
            if old[identity] != name:
                result.append("Outfit renamed: " + name)
            left, right = outfits.view(before, identity), outfits.view(after, identity)
            if any(left["fighter"][key] != right["fighter"][key] for key in outfits.APPEARANCE):
                result.append(name + ": appearance changed")
            for key, label in (
                ("textures", "texture atlases"),
                ("portrait", "portrait"),
                ("ui_art", "UI artwork"),
                ("face_sculpt", "face sculpt"),
            ):
                before_asset, after_asset = left.get(key), right.get(key)
                if key == "textures":
                    before_asset = (before_asset or {}).get("atlases", {})
                    after_asset = (after_asset or {}).get("atlases", {})
                if before_asset != after_asset:
                    result.append(name + ": " + label + " changed")
        if not result and before != after:
            result.append("Project outfit collection changed")
        return result

    def snapshot(self) -> Snapshot:
        result: Snapshot = dict(
            data=str(self.data) if self.data else None,
            profiles=[],
            selected=None,
            fields=None,
            changes=[],
            dirty=False,
            undo=False,
            style_names=STYLE_NAMES,
            limits=dict(cash=CASH_LIMIT, development=DEV_LIMIT),
            preview_error=self.preview_error,
            preview_detail=self.preview_detail,
            preview_available=self.appearance is not None,
            groups=[],
            skins=[],
            issues=self.discovery.issues if self.discovery else [],
            retail_moveset_save=self.retail_moveset_save(),
        )
        result["version"] = __version__
        result["setup"] = self.setup_view()
        result["backups"] = (
            backups.entries(self.workspace / "backups", self.profile.name)
            if self.profile and self.project is None
            else []
        )
        project_view = copy.deepcopy(self.project_source())
        if project_view is not None:
            project_view.pop("textures", None)
            project_view.pop("portrait", None)
            project_view.pop("performance", None)
            project_view.pop("outfits", None)
            project_view.pop("ui_art", None)
            project_view.pop("face_sculpt", None)
        if project_view is not None and self.metadata_edit is not None:
            project_view.update(copy.deepcopy(self.metadata_edit))
        active = self.active_view()
        from .face_geometry import CONTROLS

        sculpt = (active or {}).get("face_sculpt")
        result["face_sculpt"] = dict(
            available=self.project is not None and self.appearance is not None,
            imported=bool(sculpt and not sculpt["sliders"]),
            present=bool(sculpt),
            sliders=sculpt["sliders"] if sculpt else {},
            controls=[dict(id=k, label=v) for k, v in CONTROLS],
        )
        result["project"] = project_view
        result["project_path"] = str(self.project_path) if self.project_path else None
        result["project_origin"] = self.project_origin
        result["portrait_available"] = self.portrait_edit is not None or bool(active and "portrait" in active)
        result["outfits"] = outfits.entries(self.project_source()) if self.project else []
        result["active_outfit"] = self.active_outfit
        result["ui_art"] = (
            ui_art.status(self.project_document(validate=False), self.active_outfit) if self.project else None
        )
        textures = self.texture_edit if self.texture_edit is not None else (active or {}).get("textures", {})
        result["atlas_slots"] = sorted(textures.get("atlases", {}))
        result["blazin"] = dict(
            options=self.blazin.options if self.blazin else [], selected=self.blazin_keys(), error=self.blazin_error
        )
        key = (active or {}).get("fighter", {}).get("retail_moveset")
        if not self.project and self.profile and self.movesets:
            row = self.movesets.by_core.get(read_fields(self.current().payload)["combined_style"])
            key = row["key"] if row else None
        result["retail_movesets"] = dict(
            options=self.movesets.options if self.movesets else [], selected=key, error=self.moveset_error
        )
        from . import performance

        result["performance"] = dict(
            settings=performance.status((self.project_source() or {}).get("performance")),
            catalog=self.performance_link.catalog if self.performance_link else None,
            ai_fields=[dict(id=key, label=label) for key, label in performance.AI_FIELDS],
            project_available=self.project is not None,
        )
        if self.discovery:
            result["profiles"] = [
                dict(
                    name=p.name,
                    has_fighter=read_fields(p.container.payload)["has_fighter"],
                    legacy=p.directory_kind == "legacy",
                )
                for p in self.discovery.profiles
            ]
        if self.profile or self.project:
            result["selected"] = self.project["metadata"]["name"] if self.project else self.profile.name
            result["fields"] = read_fields(self.current().payload)
            result["changes"] = self.changes()
            result["dirty"] = (
                self.project_document(validate=False) != self.project
                if self.project
                else self.current().encode() != self.base().encode()
            )
            result["undo"] = bool(self.history)
            if self.appearance:
                fields = result["fields"]
                assert fields is not None
                result["appearance_selected"] = self.appearance.selected(fields)
                from .faces import selected

                result["face_presets"] = selected(fields, self.appearance.face_options)
                result["groups"] = [
                    dict(
                        id=str(slot),
                        label=self.group_label(slot),
                        section=self.cache.groups[str(slot)]["section"],
                        count=len(self.appearance.options[str(slot)]),
                    )
                    for slot in range(12, 38)
                    if slot not in (17, 26)
                ]
                build = "abcdef"[fields["caf_values"][0]] if fields["caf_values"][0] in range(6) else "c"
                result["skins"] = [
                    int(k[2:])
                    for k in self.cache.catalog["resources"][f"v2cp_a_{build}"]["images"]
                    if k.startswith("pl")
                ]
        from .pngs import inspect_png

        visual = result["fields"]
        key = dict(
            appearance=projects.appearance_hash(visual) if visual else None,
            outfit=self.active_outfit,
            assets=str(getattr(self.cache, "root", self.data)),
            available=result["preview_available"],
            atlases={slot: inspect_png(value, "atlas").digest for slot, value in textures.get("atlases", {}).items()},
            sculpt=(active or {}).get("face_sculpt"),
        )
        result["appearance_key"] = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
        return result

    def preview(self, changes=None, hide_clothes=False):
        if self.appearance is None:
            raise SaveError(self.preview_error or "No preview assets")
        fields = read_fields(self.current().payload)
        if not fields["has_fighter"]:
            raise SaveError("This profile has no Story fighter yet")
        if changes:
            fields.update(self.appearance.change(fields, changes))
        # Preview overlays never pass through stage/current/save. Use the game's
        # empty clothing meshes (including underwear), retaining skin/tattoos.
        if hide_clothes:
            for slot in (*range(12, 20), *range(22, 27), 28):
                fields["caf_values"][slot] = 0xFFFFFFFF
                fields["caf_colors"][slot] = 0
        result = self.cache.compose(self.appearance.outfit(fields))
        sculpt = (self.active_view() or {}).get("face_sculpt")
        if (
            self.project is not None
            and (not sculpt or sculpt["sliders"])
            and any(str(mesh.get("slot")) == "2" for mesh in result.get("meshes", []))
        ):
            from . import face_geometry

            reference = face_geometry.template(self.cache, self.appearance, fields)
            key = reference["sha256"]
            if key not in self._face_preview_basis:
                # Bounded across outfit/preset changes in a long authoring session.
                if len(self._face_preview_basis) >= 8:
                    self._face_preview_basis.clear()
                self._face_preview_basis[key] = face_geometry.preview_basis(reference)
            result["face_preview"] = self._face_preview_basis[key]
        if sculpt:
            from . import face_geometry

            reference = face_geometry.template(self.cache, self.appearance, fields)
            face_geometry.validate(sculpt, fields, reference)
            head = face_geometry.apply(dict(meshes=[m for m in result["meshes"] if m["slot"] == "2"]), sculpt)
            heads = {m["rm"]: m for m in head["meshes"]}
            result["meshes"] = [heads[m["rm"]] if m["slot"] == "2" else m for m in result["meshes"]]
            result["notices"].append(
                "Experimental template sculpt. Original rig, UVs and normals retained; extreme edits may affect shading, eyelids, hair and accessories."
            )
        textures = self.texture_edit if self.texture_edit is not None else (self.active_view() or {}).get("textures")
        if textures and textures["atlases"]:
            import base64
            import io
            from PIL import Image
            from .assets import image_uri

            for atlas in "abcd":
                if atlas not in textures["atlases"]:
                    continue
                native = Image.open(io.BytesIO(base64.b64decode(result["textures"][atlas].split(",", 1)[1]))).convert(
                    "RGBA"
                )
                imported = Image.open(io.BytesIO(projects.atlas_bytes(textures["atlases"][atlas]))).convert("RGBA")
                imported.putalpha(native.getchannel("A").resize(imported.size, Image.Resampling.NEAREST))
                result["textures"][atlas] = image_uri(imported)
            result["notices"].append(
                "Imported RGB atlases stay applied across appearance changes; original material alpha retained. Clear atlases to restore retail artwork. Injury variants apply in-game; this preview shows the normal face."
            )
        result["preview_only"] = dict(changes=changes or {}, hide_clothes=hide_clothes)
        return result

    def _clear_drafts(self):
        self.outfit_draft = self.portrait_edit = self.metadata_edit = self.texture_edit = None

    def _request_cache_clear(self, action, args):
        from . import cache_maintenance

        cache_maintenance.clear(self.workspace)
        self.cache = self.appearance = None
        self.preview_error = "The private wardrobe cache was cleared. Reopen your data folder to rebuild it."
        self.preview_detail = None
        return dict(snapshot=self.snapshot(), message="Private wardrobe cache cleared. Backups and projects are kept.")

    def _request_export_checklist(self, action, args):
        setup = self.setup_view()
        document = self.project_document(validate=False) if self.project is not None else None
        metadata = document["metadata"] if document else {}
        checks = []

        def add(key, label, ok, tab, *, note=False, detail=None):
            checks.append(
                dict(id=key, label=label, status="note" if note else "pass" if ok else "fail", tab=tab, detail=detail)
            )

        add(
            "project",
            "Project is saved; pending changes will be saved before export."
            if self.project_path
            else "Save a fighter project before exporting.",
            bool(document and self.project_path),
            "project",
        )
        add(
            "runtime",
            "Selected game version supports fighter export."
            if setup["ready"] and setup["runtime"]["features"]["export"]
            else "Choose a game version that supports fighter export in Game setup.",
            bool(setup["ready"] and setup["runtime"]["features"]["export"]),
            "setup",
        )
        add(
            "name",
            "Fighter name is set." if metadata.get("name", "").strip() else "Give your fighter a name.",
            bool(metadata.get("name", "").strip()),
            "project",
        )
        version_ok = bool(projects.VERSION.fullmatch(metadata.get("version", "")))
        add("version", "Pack version is set." if version_ok else "Set a version such as 1.0.0.", version_ok, "project")
        if document:
            view = self.active_view() or {}
            portrait = self.portrait_edit is not None or bool(view.get("portrait"))
            add(
                "portrait",
                "Portrait is present."
                if portrait
                else "Menu portraits use imported UI art or the retail donor fallback.",
                True,
                "textures",
                note=not portrait,
            )
            add("outfits", f"{len(outfits.entries(document))} outfit(s) included.", True, "outfits")
            try:
                projects.validate(copy.deepcopy(document))
                add("valid", "Project settings and embedded assets validate.", True, "project")
            except (SaveError, ValueError, KeyError, TypeError) as exc:
                add(
                    "valid",
                    "Project settings need attention. Open Details for the exact issue.",
                    False,
                    "project",
                    detail=str(exc),
                )
        return dict(checks=checks, can_export=bool(document) and all(row["status"] != "fail" for row in checks))

    def _request_donors(self, action, args):
        if (
            self.retail.catalog is None
            and self.runtime
            and self.data
            and runtimes.describe(self.runtime, self.recipe_format())["features"]["retail"]
        ):
            self.retail.request("configure", {"runtime": str(self.runtime)})
        if self.retail.catalog:
            rows = [{"key": "retail/" + row["id"], "label": row["name"]} for row in self.retail.catalog["fighters"]]
        elif self.performance_link:
            rows = [{"key": row["key"], "label": row["label"]} for row in self.performance_link.catalog["fighters"]]
        else:
            rows = []
        return dict(donors=rows)

    def request(self, action, args):
        handler = self.ACTIONS.get(action)
        if handler is None and isinstance(action, str) and action.startswith("retail_"):
            handler = self.ACTIONS["retail_*"]
        if handler is None:
            raise SaveError("Unsupported editor action")
        return handler(self, action, args)

    def _request_performance_connect(self, action, args):
        from .performance_api import Link

        if self.data is None:
            raise SaveError("Open your game data directory first")
        self.performance_link = Link(self.need_runtime(args, "tools"), self.data, self.workspace)
        return self.snapshot()

    def _request_performance_audio(self, action, args):
        if self.performance_link is None:
            raise SaveError("Connect compatible fighter tools first")
        if action == "performance_audio" and args.get("override"):
            from . import performance

            encoded = (
                self.project_document().get("performance", {}).get("voice", {}).get("clips", {}).get(args["override"])
            )
            if encoded is None:
                raise SaveError("No imported clip in this slot")
            performance.audio_bytes(encoded)
            return dict(mime="audio/wav", data=encoded)
        return (self.performance_link.voice if action == "performance_audio" else self.performance_link.animation)(args)

    def _request_performance_set(self, action, args):
        from . import performance

        if self.project is None:
            raise SaveError("Create a standalone fighter project to author performance resources")
        document = self.project_document()
        document["performance"] = performance.edited(
            document.get("performance", {}), action.removeprefix("performance_"), args, self.performance_link
        )
        candidate = projects.validate(document)
        if candidate == self.project_document():
            return self.snapshot()
        self.remember()
        self.outfit_draft = candidate
        self.edits = {}
        self.portrait_edit = self.texture_edit = self.metadata_edit = None
        return self.snapshot()

    def _request_fighting_style(self, action, args):
        mode = args.get("mode")
        if mode not in ("caf", "retail"):
            raise SaveError("Choose CAF combination or Retail fighter moveset")
        row = None
        if mode == "retail":
            if not self.movesets:
                raise SaveError(self.moveset_error)
            row = self.movesets.select(args.get("fighter"))
        if self.project is None:
            if row:
                return self.stage({"moveset_core": row["core"]})
            return self.stage({"styles": args["styles"]})
        document = self.project_document()
        if row:
            document["fighter"]["retail_moveset"] = row["key"]
        else:
            document["fighter"].pop("retail_moveset", None)
            document["fighter"]["styles"] = args["styles"]
        candidate = projects.validate(document)
        self.remember()
        self.outfit_draft = candidate
        self.edits = {}
        self.portrait_edit = self.texture_edit = self.metadata_edit = None
        return self.snapshot()

    def _request_face_export(self, action, args):
        from . import face_geometry

        if self.project is None:
            raise SaveError(
                "Create a standalone fighter project for sculpting. Story saves store original presets only."
            )
        if self.appearance is None:
            raise SaveError("Load original game assets before sculpting a face")
        document = self.project_document(validate=action != "face_clear")
        view = outfits.view(document, self.active_outfit)
        reference = face_geometry.template(self.cache, self.appearance, view["fighter"])
        if action == "face_export":
            path = Path(args["path"])
            if path.exists():
                raise SaveError("Choose a new template filename; existing files are preserved")
            from .storage import atomic_bytes

            atomic_bytes(path, face_geometry.obj(reference, view.get("face_sculpt")))
            return dict(message="Exported sculptable head OBJ. Preserve vertex order, triangulation and UVs.")
        if action == "face_clear":
            view.pop("face_sculpt", None)
        elif action == "face_sliders":
            if view.get("face_sculpt") and not view["face_sculpt"]["sliders"]:
                raise SaveError("Clear the imported sculpt before using sliders; export it first to preserve your work")
            view["face_sculpt"] = face_geometry.sliders(reference, args["values"])
        else:
            with Path(args["path"]).open("rb") as stream:
                raw = stream.read(face_geometry.MAX_OBJ + 1)
            view["face_sculpt"] = face_geometry.import_obj(raw, reference)
        candidate = projects.validate(outfits.replace_view(document, self.active_outfit, view))
        self.remember()
        self.outfit_draft, self.edits = candidate, {}
        self.portrait_edit = self.texture_edit = self.metadata_edit = None
        return dict(snapshot=self.snapshot(), message="Face sculpt staged; Save project preserves it")

    def _request_retail_action(self, action, args):
        if self.retail.data is None and self.data is None:
            # Opened straight from Home: the remembered data folder is enough for the studio, no fighter editor load.
            self.retail.data = remembered.recall(self.workspace, "data")
        result = self.retail.request(action.removeprefix("retail_"), args)
        if (
            action in ("retail_open", "retail_save")
            and self.retail.path is not None
            and self.retail.document is not None
        ):
            mode = (
                "retail-new"
                if self.retail.document.get("deployment", {}).get("mode", "add") == "add"
                else "retail-edit"
            )
            remembered.add_recent(self.workspace, mode, self.retail.path)
        return result

    def _request_ui_preview(self, action, args):
        if self.project is None:
            return {"png": None}
        effective = ui_art.resolved(self.project_document(validate=False), self.active_outfit)
        value = effective["images"].get(args["role"])
        return {
            "png": "data:image/png;base64," + value if value else None,
            "origin": effective["origins"].get(args["role"], {"source": "Retail UI donor"}),
        }

    def _request_ui_import(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project first")
        candidate = self.project_document(validate=False)
        if action == "ui_retail":
            import base64
            import tempfile
            from .fighter_mod import contract

            if self.data is None or not (Path(self.data) / "extracted").is_dir():
                raise SaveError("Load original game assets before importing retail UI artwork")
            effective = ui_art.resolved(candidate, self.active_outfit)
            self.workspace.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="ui-reference-", dir=self.workspace) as temporary:
                output = Path(temporary) / "reference"
                report = contract(
                    self.need_runtime(args, "menu"),
                    [
                        "export-ui-reference",
                        "--game",
                        str((Path(self.data) / "extracted").resolve()),
                        "--donor",
                        effective["donor"],
                        "--portrait-out",
                        str(output),
                    ],
                    temporary,
                    self.workspace,
                )
                pack = {"donor": effective["donor"], "hd_scale": effective["hd_scale"], "images": {}}
                for role, spec in report["source"]["images"].items():
                    # Source paths are generated by the reviewed runtime, but
                    # still constrain reads to this private temporary folder.
                    path = (output / spec["path"]).resolve()
                    if not path.is_relative_to(output.resolve()):
                        raise SaveError("UI reference file leaves its output folder")
                    raw = path.read_bytes()
                    if len(raw) > 4 * 1024**2:
                        raise SaveError("UI reference PNG is too large")
                    import hashlib

                    if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
                        raise SaveError("UI reference hash changed")
                    pack["images"][role] = base64.b64encode(raw).decode("ascii")
                ui_art.validate(pack)
                candidate = ui_art.upgrade(candidate)
                ui_art.node(candidate, self.active_outfit)["ui_art"] = pack
        elif action == "ui_settings":
            candidate = ui_art.edit(
                candidate, self.active_outfit, settings={"donor": args["donor"], "hd_scale": args["hd_scale"]}
            )
        else:
            raw = args.get("png")
            if raw and raw.startswith("data:image/png;base64,"):
                raw = raw.split(",", 1)[1]
            candidate = ui_art.edit(
                candidate, self.active_outfit, role=args.get("role"), png=raw, clear_all=action == "ui_clear_all"
            )
        ui_art.check_budget(candidate)
        self.remember()
        self.flush_outfit()
        self.outfit_draft = candidate
        return self.snapshot()

    def _request_outfit_select(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project before editing outfits")
        if action == "outfit_select":
            if args["id"] not in {row["id"] for row in outfits.entries(self.project_source())}:
                raise SaveError("This outfit is unavailable")
            self.flush_outfit()
            self.active_outfit = args["id"]
        else:
            candidate = self.project_document(validate=False)
            if action == "outfit_add":
                candidate, selected = outfits.add(candidate, self.active_outfit)
            elif action == "outfit_rename":
                candidate = outfits.rename(candidate, self.active_outfit, args["name"])
                selected = self.active_outfit
            else:
                candidate = outfits.remove(candidate, self.active_outfit)
                selected = outfits.DEFAULT
            self.remember()
            self.flush_outfit()
            self.outfit_draft, self.active_outfit = candidate, selected
        return self.snapshot()

    def _request_blazin(self, action, args):
        if not self.blazin:
            raise SaveError(self.blazin_error)
        rows = self.blazin.select(args["moves"])
        return self.stage(
            {"finishers": [row["record"] for row in rows]}
            if self.project
            else {"blazin_values": [row["value"] for row in rows]}
        )

    def _request_blazin_inherit(self, action, args):
        return self.stage({"finishers": None})

    def _request_project_atlas(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project first")
        if action == "project_atlas_clear":
            fields = read_fields(self.current().payload)
            textures = {"appearance_sha256": projects.appearance_hash(fields), "atlases": {}}
            if args.get("slot"):
                shown = (
                    self.texture_edit
                    if self.texture_edit is not None
                    else (self.active_view() or {}).get("textures", {})
                )
                kept = {key: value for key, value in shown.get("atlases", {}).items() if key != args["slot"]}
                textures = {
                    "appearance_sha256": shown.get("appearance_sha256", textures["appearance_sha256"]),
                    "atlases": kept,
                }
        else:
            raw = args["png"]
            if raw.startswith("data:image/png;base64,"):
                raw = raw.split(",", 1)[1]

            document = projects.with_atlas(
                outfits.view(self.project_document(), self.active_outfit), args["slot"], projects.atlas_bytes(raw)
            )
            textures = document["textures"]
        self.remember()
        self.texture_edit = textures
        return self.snapshot()

    def _request_project_portrait(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project first")
        raw = args["png"]
        if raw.startswith("data:image/png;base64,"):
            raw = raw.split(",", 1)[1]
        projects.portrait_bytes(raw)
        self.remember()
        self.portrait_edit = raw
        return self.snapshot()

    def _request_home(self, action, args):
        return dict(setup=self.setup_view(), recents=remembered.recents(self.workspace), version=__version__)

    def _request_close_project(self, action, args):
        return self.close_project()

    def _request_new_project(self, action, args):
        result = self.create_project(args["path"])
        remembered.add_recent(self.workspace, "caf", args["path"])
        return result

    def _request_open_project(self, action, args):
        result = self.open_project(args["path"])
        remembered.add_recent(self.workspace, "caf", args["path"])
        return result

    def _request_project_metadata_draft(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project first")
        # Preserve incomplete form values; validate only when saving/exporting.
        if set(args) != {"metadata", "identity"} or not all(isinstance(args[k], dict) for k in args):
            raise SaveError("Invalid project details")
        self.metadata_edit = copy.deepcopy(args)
        if all(self.project.get(k) == v for k, v in args.items()):
            self.metadata_edit = None
        return self.snapshot()

    def _request_project_metadata(self, action, args):
        if self.project is None:
            raise SaveError("Create or open a fighter project first")
        document = self.project_document()
        document["metadata"].update(args["metadata"])
        if "identity" in args:
            document["identity"] = args["identity"]
        projects.validate(document)
        self.project_hash = projects.write(self.project_path, document, self.project_hash)
        self.project, self.edits, self.history = document, {}, []
        self._clear_drafts()
        return dict(snapshot=self.snapshot(), message="Saved fighter project and pack details")

    def _request_export_mod(self, action, args):
        from .fighter_mod import export_mod

        if self.project is None:
            raise SaveError("Create or open a fighter project before exporting a mod")
        report = export_mod(
            self.project_document(),
            args["path"],
            self.need_runtime(args, "export"),
            self.data,
            self.workspace / "fighter-exports",
            progress=self.progress,
            asset_cache=self.cache,
        )
        self.last_export = Path(args["path"])
        return dict(
            message="Validated Custom Fighter Mod exported to " + args["path"],
            report=report,
            summary=self.export_summary(Path(args["path"]), report),
        )

    def _request_setup_scan(self, action, args):
        folder = args.get("folder") or remembered.recall(self.workspace, "app") or runtimes.default_folder()
        if not folder or not Path(folder).is_dir():
            result = dict(folder=None, candidates=[], data=None, current=None)
        else:
            result = runtimes.scan(folder, self.recipe_format())
        result["warning"] = remembered.take_warning(self.workspace)
        return result

    def _request_setup_use(self, action, args):
        runtime = Path(args["runtime"]).resolve()
        row = runtimes.describe(runtime, self.recipe_format())
        if not row["usable"]:
            raise SaveError("That is not a game version: scripts/fighter-contract.py is missing")
        if self.runtime != runtime:
            self.performance_link = None
            self.retail.runtime = self.retail.catalog = None
        self.runtime = runtime
        remembered.remember(self.workspace, "runtime", runtime)
        if args.get("folder"):
            remembered.remember(self.workspace, "app", args["folder"])
        data = args.get("data")
        if (
            data
            and remembered.data_ok(data)
            and (self.data is None or Path(data).resolve() != Path(self.data).resolve())
        ):
            remembered.remember(self.workspace, "data", data)
            return self.open_data(data)
        return self.snapshot()

    def _request_open_data(self, action, args):
        return self.open_data(args["path"])

    def _request_snapshot(self, action, args):
        return self.snapshot()

    def _request_select_profile(self, action, args):
        return self.select_profile(args["name"])

    def _request_stage(self, action, args):
        return self.stage(args["edits"])

    def _request_appearance(self, action, args):
        return self.stage_appearance(args["changes"])

    def _request_options(self, action, args):
        if self.appearance is None or args["slot"] not in self.appearance.options:
            raise SaveError("No appearance choices for that category")
        return [
            {k: v for k, v in row.items() if k not in {"selection", "value", "color"}}
            for row in self.appearance.options[args["slot"]]
        ]

    def _request_preview(self, action, args):
        return self.preview(args.get("changes"), bool(args.get("hide_clothes", False)))

    def _request_undo(self, action, args):
        if self.history:
            for key, value in self.history.pop().items():
                setattr(self, key, value)
        return self.snapshot()

    def _request_reset(self, action, args):
        self.edits, self.history = {}, []
        self._clear_drafts()
        if self.project and self.active_outfit not in {row["id"] for row in outfits.entries(self.project)}:
            self.active_outfit = outfits.DEFAULT
        return self.snapshot()

    def _request_save(self, action, args):
        if self.project is not None:
            document = self.project_document()
            self.project_hash = projects.write(self.project_path, document, self.project_hash)
            self.project, self.edits, self.history = document, {}, []
            self._clear_drafts()
            return dict(snapshot=self.snapshot(), message="Saved fighter project")
        notice = self.retail_moveset_save()
        if notice and args.get("acknowledge_retail_moveset") is not True:
            raise SaveError(notice)
        name = self.profile.name
        backup = save_profile(self.profile, self.current(), self.workspace / "backups")
        return dict(
            snapshot=self.select_profile(name),
            message="Saved profile. Backup: " + str(backup),
            summary=dict(
                title="Profile saved",
                folder="backups",
                lines=[
                    "Saved " + name + ".",
                    "Backup of the previous save: " + backup.name,
                    "Restore it any time from Backups in the left column.",
                ],
            ),
        )

    def _request_restore_backup(self, action, args):
        if self.project is not None or self.profile is None:
            raise SaveError("Choose a Story profile to restore a backup into")
        name = self.profile.name
        before = backups.restore(self.profile, self.workspace / "backups", args.get("id"))
        return dict(
            snapshot=self.select_profile(name),
            message="Restored a backup of " + name,
            summary=dict(
                title="Backup restored",
                folder="backups",
                lines=[
                    "Restored " + name + " from " + args["id"] + ".",
                    "The save it replaced was backed up first: " + before.name,
                ],
            ),
        )

    def _request_export(self, action, args):
        if self.project is not None:
            self.project_hash = projects.write(args["path"], self.project_document())
            self.project_path = Path(args["path"])
            self.project, self.edits, self.history = self.project_document(), {}, []
            self._clear_drafts()
            return dict(snapshot=self.snapshot(), message="Saved project copy")
        export_profile(self.profile, self.current(), Path(args["path"]))
        self.last_export = Path(args["path"])
        return dict(
            message="Exported complete profile to " + args["path"],
            summary=dict(
                title="Profile exported",
                folder="export",
                lines=["Saved to " + args["path"], "Import it from the left column to install it as a profile."],
            ),
        )

    def _request_duplicate(self, action, args):
        if self.project is not None:
            raise SaveError("Use Save project as to copy a standalone fighter")
        duplicate(self.profile, self.current(), args["name"])
        return dict(snapshot=self.select_profile(args["name"]), message="Created profile " + args["name"])

    def _request_import(self, action, args):
        name, _, files = read_archive(Path(args["path"]))
        install_files(self.discovery.title_root, name, files)
        return dict(snapshot=self.select_profile(name), message="Imported complete profile " + name)

    ACTIONS = {
        "export_checklist": _request_export_checklist,
        "donors": _request_donors,
        "cache_clear": _request_cache_clear,
        "performance_connect": _request_performance_connect,
        "performance_audio": _request_performance_audio,
        "performance_animation": _request_performance_audio,
        "performance_set": _request_performance_set,
        "performance_clip": _request_performance_set,
        "performance_clear": _request_performance_set,
        "fighting_style": _request_fighting_style,
        "face_export": _request_face_export,
        "face_import": _request_face_export,
        "face_sliders": _request_face_export,
        "face_clear": _request_face_export,
        "retail_*": _request_retail_action,
        "ui_preview": _request_ui_preview,
        "ui_import": _request_ui_import,
        "ui_clear": _request_ui_import,
        "ui_clear_all": _request_ui_import,
        "ui_settings": _request_ui_import,
        "ui_retail": _request_ui_import,
        "outfit_select": _request_outfit_select,
        "outfit_add": _request_outfit_select,
        "outfit_rename": _request_outfit_select,
        "outfit_remove": _request_outfit_select,
        "blazin": _request_blazin,
        "blazin_inherit": _request_blazin_inherit,
        "project_atlas": _request_project_atlas,
        "project_atlas_clear": _request_project_atlas,
        "project_portrait": _request_project_portrait,
        "home": _request_home,
        "close_project": _request_close_project,
        "new_project": _request_new_project,
        "open_project": _request_open_project,
        "project_metadata_draft": _request_project_metadata_draft,
        "project_metadata": _request_project_metadata,
        "export_mod": _request_export_mod,
        "setup_scan": _request_setup_scan,
        "setup_use": _request_setup_use,
        "open_data": _request_open_data,
        "snapshot": _request_snapshot,
        "select_profile": _request_select_profile,
        "stage": _request_stage,
        "appearance": _request_appearance,
        "options": _request_options,
        "preview": _request_preview,
        "undo": _request_undo,
        "reset": _request_reset,
        "save": _request_save,
        "restore_backup": _request_restore_backup,
        "export": _request_export,
        "duplicate": _request_duplicate,
        "import": _request_import,
    }
