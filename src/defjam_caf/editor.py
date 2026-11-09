"""Desktop-independent editor session; all mutations are explicit actions."""
import copy
from pathlib import Path

from .appearance import Appearance
from .assets import build_cache
from .container import SaveError
from .fields import apply_fields, read_fields, STYLE_NAMES, CASH_LIMIT, DEV_LIMIT
from .profiles import discover
from .storage import save_profile, export_profile, duplicate, read_archive, install_files
from . import projects


class Editor:
    def group_label(self, slot):
        if slot == 25:
            return "Earrings (pair)"
        if slot >= 29:
            return "Tattoo - " + ("Head & Neck", "Chest & Stomach", "Back", "Left Arm", "Left Forearm",
                                  "Right Arm", "Right Forearm", "Left Leg", "Right Leg")[slot - 29]
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
        self.preview_error = None
        self.project = self.project_path = self.project_hash = None
        self.portrait_edit = None
        self.metadata_edit = None
        self._project_base_document = self._project_base = None

    def base(self):
        if self.project is not None:
            if self._project_base_document is not self.project:
                self._project_base = projects.container(self.project)
                self._project_base_document = self.project
            return self._project_base
        if self.profile is None:
            raise SaveError("Choose a profile or open a fighter project first")
        return self.profile.container

    def project_document(self):
        document = copy.deepcopy(self.project)
        if self.metadata_edit is not None:
            document.update(copy.deepcopy(self.metadata_edit))
        fields = read_fields(self.current().payload)
        document["fighter"] = {k: copy.deepcopy(fields[k]) for k in document["fighter"]}
        if self.portrait_edit is not None:
            document["portrait"] = self.portrait_edit
        return projects.validate(document)

    def create_project(self, path):
        fields = read_fields(self.current().payload)
        document = projects.from_fields(fields, self.profile.name if self.profile else self.project["metadata"]["name"])
        if self.project is not None:
            source = self.project_document()
            document["metadata"] = copy.deepcopy(source["metadata"])
            if "portrait" in source:
                document["portrait"] = source["portrait"]
        digest = projects.write(path, document)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.profile = None
        self.portrait_edit = self.metadata_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_project(self, path):
        document, digest = projects.read(path)
        self.project, self.project_path, self.project_hash = document, Path(path), digest
        self.profile = None
        self.portrait_edit = self.metadata_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def open_data(self, data):
        data = Path(data).expanduser().resolve()
        result = discover(data)
        self.data, self.discovery = data, result
        self.cache = self.appearance = None
        self.preview_error = None
        if (data / "extracted").is_dir():
            try:
                self.cache = build_cache(data / "extracted", self.workspace, self.progress)
                self.appearance = Appearance(self.cache)
            except (OSError, ValueError, KeyError) as exc:
                self.preview_error = "CAF cache could not be loaded: " + str(exc)
        else:
            self.preview_error = "Choose the Recomp data directory containing extracted game assets for the 3D preview."
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

    def select_profile(self, name):
        self.discovery = discover(self.data)
        self.profile = next((p for p in self.discovery.profiles if p.name == name), None)
        if self.profile is None:
            raise SaveError("Profile is unavailable; refresh the data directory")
        self.project = self.project_path = self.project_hash = None
        self.portrait_edit = self.metadata_edit = None
        self.edits, self.history = {}, []
        return self.snapshot()

    def current(self):
        return apply_fields(self.base(), self.edits)

    def stage(self, changes):
        if self.project is not None and set(changes) & {"cash", "development"}:
            raise SaveError("Fighter projects have no Story currency")
        if not read_fields(self.current().payload)["has_fighter"]:
            raise SaveError("This profile has no Story fighter. Create one in the game first")
        previous = copy.deepcopy(self.edits)
        combined = copy.deepcopy(self.edits)
        if "stats" in changes:
            combined["stats"] = dict(combined.get("stats", {}), **changes["stats"])
        combined.update({k: v for k, v in changes.items() if k != "stats"})
        candidate = apply_fields(self.base(), combined)
        if candidate.payload == self.current().payload:
            return self.snapshot()
        self.history.append(previous)
        self.history = self.history[-100:]
        self.edits = combined
        return self.snapshot()

    def stage_appearance(self, changes):
        if self.appearance is None:
            raise SaveError("Load the original game assets before changing appearance")
        fields = read_fields(self.current().payload)
        edited = self.appearance.change(fields, changes)
        # Validate a complete source outfit before any bytes can be staged.
        try:
            self.cache.compose(self.appearance.outfit(dict(fields, **edited)))
        except KeyError as exc:
            raise SaveError("This item combination cannot be previewed yet; the existing appearance was preserved") from exc
        return self.stage(edited)

    def changes(self):
        if self.profile is None and self.project is None:
            return []
        before, after = read_fields(self.base().payload), read_fields(self.current().payload)
        result = []
        if self.metadata_edit is not None:
            result.append("Project details changed")
        if self.portrait_edit is not None:
            result.append("Project portrait changed")
        for key, label in (("cash", "Cash"), ("development", "Development points")):
            if before[key] != after[key]:
                result.append(f"{label}: {before[key]:,} → {after[key]:,}")
        for key in before["stats"]:
            if before["stats"][key] != after["stats"][key]:
                result.append(f"{key.capitalize()}: {before['stats'][key]} → {after['stats'][key]}")
        if before["styles"] != after["styles"]:
            result.append("Fighting styles: " + ", ".join(STYLE_NAMES[i] for i in after["styles"]))
        for slot, (old, new, oc, nc) in enumerate(zip(before["caf_values"], after["caf_values"], before["caf_colors"], after["caf_colors"])):
            if old != new or oc != nc:
                label = {0: "Body build", 1: "Skin tone"}.get(slot)
                if not label and self.cache:
                    label = self.group_label(slot)
                result.append((label or "Appearance") + " changed")
        return result

    def snapshot(self):
        result = dict(data=str(self.data) if self.data else None, profiles=[], selected=None,
                      fields=None, changes=[], dirty=False, undo=False,
                      style_names=STYLE_NAMES, limits=dict(cash=CASH_LIMIT, development=DEV_LIMIT),
                      preview_error=self.preview_error, preview_available=self.appearance is not None,
                      groups=[], skins=[], issues=self.discovery.issues if self.discovery else [])
        project_view = copy.deepcopy(self.project)
        if project_view is not None and self.metadata_edit is not None:
            project_view.update(copy.deepcopy(self.metadata_edit))
        result.update(project=project_view, project_path=str(self.project_path) if self.project_path else None,
                      portrait_available=self.portrait_edit is not None or bool(self.project and "portrait" in self.project))
        if self.discovery:
            result["profiles"] = [dict(name=p.name, has_fighter=read_fields(p.container.payload)["has_fighter"],
                                       legacy=p.directory_kind == "legacy") for p in self.discovery.profiles]
        if self.profile or self.project:
            result.update(selected=self.project["metadata"]["name"] if self.project else self.profile.name,
                          fields=read_fields(self.current().payload),
                          changes=self.changes(), dirty=self.current().encode() != self.base().encode() or self.portrait_edit is not None or self.metadata_edit is not None,
                          undo=bool(self.history))
            if self.appearance:
                fields = result["fields"]
                result["appearance_selected"] = self.appearance.selected(fields)
                result["groups"] = [dict(id=str(slot), label=self.group_label(slot),
                                          section=self.cache.groups[str(slot)]["section"], count=len(self.appearance.options[str(slot)]))
                                    for slot in range(12, 38) if slot not in (17, 26)]
                build = "abcdef"[fields["caf_values"][0]] if fields["caf_values"][0] in range(6) else "c"
                result["skins"] = [int(k[2:]) for k in self.cache.catalog["resources"][f"v2cp_a_{build}"]["images"] if k.startswith("pl")]
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
                fields["caf_values"][slot] = 0xffffffff
                fields["caf_colors"][slot] = 0
        result = self.cache.compose(self.appearance.outfit(fields))
        result["preview_only"] = dict(changes=changes or {}, hide_clothes=hide_clothes)
        return result

    def request(self, action, args):
        if action == "project_portrait":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            raw = args["png"]
            if raw.startswith("data:image/png;base64,"):
                raw = raw.split(",", 1)[1]
            projects.portrait_bytes(raw)
            self.portrait_edit = raw
            return self.snapshot()
        if action == "new_project":
            return self.create_project(args["path"])
        if action == "open_project":
            return self.open_project(args["path"])
        if action == "project_metadata_draft":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            # Preserve incomplete form values; validate only when saving/exporting.
            if set(args) != {"metadata", "identity"} or not all(isinstance(args[k], dict) for k in args):
                raise SaveError("Invalid project details")
            self.metadata_edit = copy.deepcopy(args)
            if all(self.project.get(k) == v for k, v in args.items()):
                self.metadata_edit = None
            return self.snapshot()
        if action == "project_metadata":
            if self.project is None:
                raise SaveError("Create or open a fighter project first")
            document = self.project_document()
            document["metadata"].update(args["metadata"])
            if "identity" in args:
                document["identity"] = args["identity"]
            projects.validate(document)
            self.project_hash = projects.write(self.project_path, document, self.project_hash)
            self.project, self.edits, self.history = document, {}, []
            self.portrait_edit = self.metadata_edit = None
            return dict(snapshot=self.snapshot(), message="Saved fighter project and pack details")
        if action == "export_mod":
            from .fighter_mod import export_mod
            if self.project is None:
                raise SaveError("Create or open a fighter project before exporting a mod")
            report = export_mod(self.project_document(), args["path"], args["runtime"], self.data,
                                self.workspace / "fighter-exports", progress=self.progress)
            return dict(message="Validated Custom Fighter Mod exported to " + args["path"], report=report)
        if action == "open_data":
            return self.open_data(args["path"])
        if action == "snapshot":
            return self.snapshot()
        if action == "select_profile":
            return self.select_profile(args["name"])
        if action == "stage":
            return self.stage(args["edits"])
        if action == "appearance":
            return self.stage_appearance(args["changes"])
        if action == "options":
            if self.appearance is None or args["slot"] not in self.appearance.options:
                raise SaveError("No appearance choices for that category")
            return [{k: v for k, v in row.items() if k not in {"selection", "value", "color"}}
                    for row in self.appearance.options[args["slot"]]]
        if action == "preview":
            return self.preview(args.get("changes"), bool(args.get("hide_clothes", False)))
        if action == "undo":
            if self.history:
                self.edits = self.history.pop()
            return self.snapshot()
        if action == "reset":
            self.edits, self.history = {}, []
            self.portrait_edit = self.metadata_edit = None
            return self.snapshot()
        if action == "save":
            if self.project is not None:
                document = self.project_document()
                self.project_hash = projects.write(self.project_path, document, self.project_hash)
                self.project, self.edits, self.history = document, {}, []
                self.portrait_edit = self.metadata_edit = None
                return dict(snapshot=self.snapshot(), message="Saved fighter project")
            backup = save_profile(self.profile, self.current(), self.workspace / "backups")
            return dict(snapshot=self.select_profile(self.profile.name), message="Saved profile. Backup: " + str(backup))
        if action == "export":
            if self.project is not None:
                self.project_hash = projects.write(args["path"], self.project_document())
                self.project_path = Path(args["path"])
                self.project, self.edits, self.history = self.project_document(), {}, []
                self.portrait_edit = self.metadata_edit = None
                return dict(snapshot=self.snapshot(), message="Saved project copy")
            export_profile(self.profile, self.current(), Path(args["path"]))
            return dict(message="Exported complete profile to " + args["path"])
        if action == "duplicate":
            if self.project is not None:
                raise SaveError("Use Save project as to copy a standalone fighter")
            path = duplicate(self.profile, self.current(), args["name"])
            return dict(snapshot=self.select_profile(args["name"]), message="Created profile " + args["name"])
        if action == "import":
            name, _, files = read_archive(Path(args["path"]))
            install_files(self.discovery.title_root, name, files)
            return dict(snapshot=self.select_profile(name), message="Imported complete profile " + name)
        raise SaveError("Unsupported editor action")
