"""Native chooser preparation; dialogs stay on the GUI thread, work runs in Editor."""

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable
from PySide6.QtWidgets import QFileDialog, QInputDialog
from . import projects, remembered, retail, runtimes
from .container import SaveError
from .locations import default_data_directory


@dataclass(frozen=True)
class Prepared:
    action: str | None = None
    args: dict = field(default_factory=dict)
    result: object = None


@dataclass(frozen=True)
class DialogSpec:
    prepare: Callable | None = None
    kind: str = "open"
    title: str = ""
    filter: str = ""
    to_action: str = ""
    default: str = ""


class Dialogs:
    def __init__(self, bridge):
        self.window = bridge.window
        self.editor = bridge.editor
        self.runtime_folder = bridge.runtime_folder

    def prepare(self, action, args):
        spec = self.SPECS.get(action)
        if spec is None:
            if action.startswith("choose_"):
                raise SaveError("Unsupported native dialog")
            return Prepared(action, args)
        if spec.prepare is not None:
            return spec.prepare(self, action, args)
        dialog = QFileDialog.getOpenFileName if spec.kind == "open" else QFileDialog.getSaveFileName
        path, _ = dialog(self.window, spec.title, spec.default, spec.filter)
        return Prepared(spec.to_action, {"path": path}) if path else Prepared()

    def _prepare_retail_copy(self, action, args):
        operation = action.removeprefix("choose_retail_")
        session = self.editor.retail
        if operation in ("runtime", "data", "import"):
            title = {
                "runtime": "Select compatible Custom Fighter runtime checkout",
                "data": "Select Recomp data directory",
                "import": "Select ordinary fighter pack folder",
            }[operation]
            path = QFileDialog.getExistingDirectory(self.window, title)
            if not path:
                return Prepared(result=None)
            if operation == "runtime":
                remembered.remember(self.editor.workspace, "runtime", path)
            if operation == "data":
                data = Path(path).resolve()
                if not (data / "extracted").is_dir():
                    raise SaveError("Choose the data directory containing extracted")
                remembered.remember(self.editor.workspace, "data", data)
                session.data = data
                session.catalog = None
                return Prepared(result=session.snapshot())
            if operation == "import":
                manifest = retail.read_manifest(path)
                labels = [f["id"] + " · " + f["name"] for f in manifest["fighters"]]
                if not labels:
                    labels = [r["target"] + " · Retail appearance override" for r in manifest.get("overrides", [])]
                label, ok = QInputDialog.getItem(self.window, "Import fighter", "Choose one fighter", labels, 0, False)
                if not ok:
                    return Prepared(result=None)
                action, args = "retail_import", {"folder": path, "fighter": label.split(" · ", 1)[0]}
            else:
                action, args = "retail_configure", {"runtime": path}
        elif operation in ("open", "save", "copy", "export"):
            if operation == "save" and session.path:
                action, args = "retail_save", {}
            else:
                opening = operation == "open"
                exporting = operation == "export"
                dialog = QFileDialog.getOpenFileName if opening else QFileDialog.getSaveFileName
                path, _ = dialog(
                    self.window,
                    "Open retail fighter project"
                    if opening
                    else "Export Custom Fighter Mod"
                    if exporting
                    else "Save retail fighter project",
                    "" if opening else "fighter.zip" if exporting else "fighter.ffnyfighter",
                    "Fighter mod (*.zip)" if exporting else "Fighter projects (*.ffnyfighter)",
                )
                if not path:
                    return Prepared(result=None)
                action, args = (
                    "retail_" + ("open" if opening else "export" if exporting else "save"),
                    {"path": path},
                )
        elif operation in ("ui", "texture"):
            path, _ = QFileDialog.getOpenFileName(self.window, "Import fighter artwork", "", "PNG image (*.png)")
            if not path:
                return Prepared(result=None)
            import base64

            limit = (16 if operation == "texture" else 4) * 1024**2
            with Path(path).open("rb") as stream:
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise SaveError("PNG exceeds " + str(limit // 1024**2) + " MiB")
            action, args = "retail_" + operation, {**args, "png": base64.b64encode(raw).decode("ascii")}
        else:
            raise SaveError("Unsupported retail dialog")
        return Prepared(action, args)

    def _prepare_setup_folder(self, action, args):
        start = remembered.recall(self.editor.workspace, "app") or runtimes.default_folder() or Path.home()
        path = QFileDialog.getExistingDirectory(
            self.window, "Choose your Def Jam Recompiled folder, or a source checkout", str(start)
        )
        if not path:
            return Prepared(result=None)
        action, args = "setup_scan", {"folder": path}
        return Prepared(action, args)

    def _prepare_data(self, action, args):
        path = QFileDialog.getExistingDirectory(
            self.window,
            "Select Recomp data directory",
            str(self.editor.data or default_data_directory() or Path.home()),
        )
        if not path:
            return Prepared(result=None)
        remembered.remember(self.editor.workspace, "data", path)
        action, args = "open_data", {"path": path}
        return Prepared(action, args)

    def _prepare_export(self, action, args):
        if self.editor.profile is None:
            raise SaveError("Choose a profile first")
        path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Export complete profile",
            self.editor.profile.name + ".djprofile",
            "FFNY profiles (*.djprofile)",
        )
        if not path:
            return Prepared(result=None)
        action, args = "export", {"path": path}
        return Prepared(action, args)

    def _prepare_performance_tools(self, action, args):
        runtime = self.runtime_folder("tools")
        if not runtime:
            return Prepared(result=None)
        action, args = "performance_connect", dict(runtime=runtime)
        return Prepared(action, args)

    def _prepare_voice_clip(self, action, args):
        import base64

        path, _ = QFileDialog.getOpenFileName(self.window, "Import mono PCM16 voice clip", "", "WAV audio (*.wav)")
        if not path:
            return Prepared(result=None)
        with Path(path).open("rb") as stream:
            audio = stream.read(8 * 1024**2 + 1)
        if len(audio) > 8 * 1024**2:
            raise SaveError("Voice clip exceeds 8 MiB")
        action, args = (
            "performance_clip",
            dict(target=args["target"], wav=base64.b64encode(audio).decode("ascii")),
        )
        return Prepared(action, args)

    def _prepare_mod_export(self, action, args):
        runtime = self.runtime_folder("export")
        if not runtime:
            return Prepared(result=None)
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Export validated Custom Fighter Mod", "fighter-mod.zip", "Fighter mod (*.zip)"
        )
        if not path:
            return Prepared(result=None)
        action, args = "export_mod", {"path": path, "runtime": runtime}
        return Prepared(action, args)

    def _prepare_ui_retail(self, action, args):
        runtime = self.runtime_folder("menu")
        if not runtime:
            return Prepared(result=None)
        action, args = "ui_retail", {"runtime": runtime}
        return Prepared(action, args)

    def _prepare_project_atlas(self, action, args):
        import base64

        atlas = action == "choose_project_atlas"
        title = (
            "Import 256–2048px square RGB atlas"
            if atlas
            else "Import fighter UI artwork"
            if action == "choose_ui_art"
            else "Import fighter portrait"
        )
        path, _ = QFileDialog.getOpenFileName(self.window, title, "", "PNG image (*.png)")
        if not path:
            return Prepared(result=None)
        limit = projects.MAX_ATLAS_BYTES if atlas else 4 * 1024 * 1024
        with Path(path).open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise SaveError("Atlas PNG is too large" if atlas else "Portrait PNG is too large")
        action, args = (
            ("project_atlas", {"slot": args["slot"], "png": base64.b64encode(raw).decode("ascii")})
            if atlas
            else (
                ("ui_import", {"role": args["role"], "png": base64.b64encode(raw).decode("ascii")})
                if action == "choose_ui_art"
                else ("project_portrait", {"png": base64.b64encode(raw).decode("ascii")})
            )
        )
        return Prepared(action, args)

    def _prepare_import(self, action, args):
        if self.editor.discovery is None:
            raise SaveError("Choose the destination data directory first")
        path, _ = QFileDialog.getOpenFileName(self.window, "Import complete profile", "", "FFNY profiles (*.djprofile)")
        if not path:
            return Prepared(result=None)
        action, args = "import", {"path": path}
        return Prepared(action, args)

    def _prepare_duplicate(self, action, args):
        name, ok = QInputDialog.getText(
            self.window, "Duplicate fighter profile", "New profile ID (1–7 uppercase letters or digits):"
        )
        if not ok:
            return Prepared(result=None)
        action, args = "duplicate", {"name": name.strip().upper()}
        return Prepared(action, args)

    SPECS = {
        "choose_retail_runtime": DialogSpec(_prepare_retail_copy),
        "choose_retail_data": DialogSpec(_prepare_retail_copy),
        "choose_retail_import": DialogSpec(_prepare_retail_copy),
        "choose_retail_open": DialogSpec(_prepare_retail_copy),
        "choose_retail_save": DialogSpec(_prepare_retail_copy),
        "choose_retail_copy": DialogSpec(_prepare_retail_copy),
        "choose_retail_export": DialogSpec(_prepare_retail_copy),
        "choose_retail_ui": DialogSpec(_prepare_retail_copy),
        "choose_retail_texture": DialogSpec(_prepare_retail_copy),
        "choose_setup_folder": DialogSpec(_prepare_setup_folder),
        "choose_data": DialogSpec(_prepare_data),
        "choose_export": DialogSpec(_prepare_export),
        "choose_project_copy": DialogSpec(
            kind="save",
            title="Save standalone fighter project",
            filter="Fighter projects (*.ffnyfighter)",
            to_action="export",
            default="fighter.ffnyfighter",
        ),
        "choose_project": DialogSpec(
            title="Open fighter project", filter="Fighter projects (*.ffnyfighter)", to_action="open_project"
        ),
        "choose_new_project": DialogSpec(
            kind="save",
            title="Save standalone fighter project",
            filter="Fighter projects (*.ffnyfighter)",
            to_action="new_project",
            default="fighter.ffnyfighter",
        ),
        "choose_performance_tools": DialogSpec(_prepare_performance_tools),
        "choose_voice_clip": DialogSpec(_prepare_voice_clip),
        "choose_mod_export": DialogSpec(_prepare_mod_export),
        "choose_face_export": DialogSpec(
            kind="save",
            title="Export head template",
            filter="Wavefront head (*.obj)",
            to_action="face_export",
            default="head-template.obj",
        ),
        "choose_face_import": DialogSpec(
            title="Import sculpted head", filter="Wavefront head (*.obj)", to_action="face_import"
        ),
        "choose_ui_retail": DialogSpec(_prepare_ui_retail),
        "choose_ui_art": DialogSpec(_prepare_project_atlas),
        "choose_project_atlas": DialogSpec(_prepare_project_atlas),
        "choose_project_portrait": DialogSpec(_prepare_project_atlas),
        "choose_import": DialogSpec(_prepare_import),
        "choose_duplicate": DialogSpec(_prepare_duplicate),
    }
