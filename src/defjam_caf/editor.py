"""Desktop-independent editor session; all mutations are explicit actions."""
import copy
from pathlib import Path

from .appearance import Appearance
from .assets import build_cache
from .container import SaveError
from .fields import apply_fields, read_fields, STYLE_NAMES, CASH_LIMIT, DEV_LIMIT
from .profiles import discover
from .storage import save_profile, export_profile, duplicate, read_archive, install_files


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

    def open_data(self, data):
        data = Path(data).expanduser().resolve()
        result = discover(data)
        self.data, self.discovery = data, result
        self.cache = self.appearance = None
        self.preview_error = None
        if (data / "extracted" / "assets" / "v2cp_0.viv").is_file():
            try:
                self.cache = build_cache(data / "extracted", self.workspace, self.progress)
                self.appearance = Appearance(self.cache)
            except (OSError, ValueError, KeyError) as exc:
                self.preview_error = "CAF cache could not be loaded: " + str(exc)
        else:
            self.preview_error = "Choose the Recomp data directory containing extracted game assets for the 3D preview."
        candidates = [p for p in result.profiles if read_fields(p.container.payload)["has_fighter"]]
        chosen = max(candidates or result.profiles, key=lambda p: p.path.stat().st_mtime, default=None)
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
        self.edits, self.history = {}, []
        return self.snapshot()

    def current(self):
        if self.profile is None:
            raise SaveError("Choose a profile first")
        return apply_fields(self.profile.container, self.edits)

    def stage(self, changes):
        if not read_fields(self.current().payload)["has_fighter"]:
            raise SaveError("This profile has no Story fighter. Create one in the game first")
        previous = copy.deepcopy(self.edits)
        combined = copy.deepcopy(self.edits)
        if "stats" in changes:
            combined["stats"] = dict(combined.get("stats", {}), **changes["stats"])
        combined.update({k: v for k, v in changes.items() if k != "stats"})
        candidate = apply_fields(self.profile.container, combined)
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
        if self.profile is None:
            return []
        before, after = read_fields(self.profile.container.payload), read_fields(self.current().payload)
        result = []
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
        if self.discovery:
            result["profiles"] = [dict(name=p.name, has_fighter=read_fields(p.container.payload)["has_fighter"],
                                       legacy=p.directory_kind == "legacy") for p in self.discovery.profiles]
        if self.profile:
            result.update(selected=self.profile.name, fields=read_fields(self.current().payload),
                          changes=self.changes(), dirty=self.current().encode() != self.profile.container.encode(),
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
            return self.snapshot()
        if action == "save":
            backup = save_profile(self.profile, self.current(), self.workspace / "backups")
            return dict(snapshot=self.select_profile(self.profile.name), message="Saved profile. Backup: " + str(backup))
        if action == "export":
            export_profile(self.profile, self.current(), Path(args["path"]))
            return dict(message="Exported complete profile to " + args["path"])
        if action == "duplicate":
            path = duplicate(self.profile, self.current(), args["name"])
            return dict(snapshot=self.select_profile(args["name"]), message="Created profile " + args["name"])
        if action == "import":
            name, _, files = read_archive(Path(args["path"]))
            install_files(self.discovery.title_root, name, files)
            return dict(snapshot=self.select_profile(name), message="Imported complete profile " + name)
        raise SaveError("Unsupported editor action")
