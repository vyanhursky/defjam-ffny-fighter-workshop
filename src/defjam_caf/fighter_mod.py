"""Custom Fighter pack export through the matching runtime's shared compiler."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from .container import SaveError
from .projects import validate, portrait_bytes, atlas_bytes, require, SCHEMA2, SCHEMA3


def run_contract(runtime, output, arguments):
    """Frozen editor helper: execute the selected development runtime's API.

    Separate process and output file also work in Windows windowed bundles,
    where stdout/stderr are absent. Never run conversion code from a mod pack.
    """
    import contextlib
    import runpy
    runtime, output = Path(runtime).resolve(), Path(output)
    script = runtime / "scripts/fighter-contract.py"
    require(script.is_file(), "Fighter authoring API is missing")
    sys.dont_write_bytecode = True
    sys.argv = [str(script), *arguments]
    sys.path.insert(0, str(runtime / "setup"))
    with output.open("x", encoding="utf-8") as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            try:
                runpy.run_path(str(script), run_name="__main__")
            except SystemExit as exc:
                return exc.code or 0
    return 0


def contract(runtime, arguments, temporary, workspace):
    helper_output = Path(temporary) / ("contract-" + str(len(list(Path(temporary).glob("contract-*.json")))) + ".json")
    command = ([sys.executable, "--fighter-contract", str(runtime), str(helper_output), *arguments]
               if getattr(sys, "frozen", False) else
               [sys.executable, "-B", str(runtime / "scripts/fighter-contract.py"), *arguments])
    environment = dict(os.environ, TMPDIR=str(workspace.resolve()), TEMP=str(workspace.resolve()), TMP=str(workspace.resolve()))
    try:
        result = subprocess.run(command, cwd=runtime, env=environment, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise SaveError("Fighter runtime validation timed out; no mod was published") from exc
    output = helper_output.read_text(encoding="utf-8") if helper_output.is_file() else result.stdout
    if result.returncode:
        raise SaveError("Fighter runtime validation refused the export: " + (result.stderr or output)[-3000:])
    try:
        report = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise SaveError("Fighter runtime returned an invalid validation receipt") from exc
    require(type(report) is dict and report.get("ok") is True, "Runtime did not confirm the operation")
    return report


def export_mod(project, destination, runtime, data, workspace, progress=lambda _: None):
    validate(project)
    destination, runtime, workspace = Path(destination), Path(runtime).resolve(), Path(workspace)
    require(data is not None, "Open your Recomp data directory before exporting a fighter mod")
    require(not destination.exists(), "Mod export destination already exists")
    require((runtime / "setup/fighter_caf.py").is_file() and (runtime / "scripts/fighter-contract.py").is_file(),
            "This runtime has no CAF recipe support. Select the compatible Custom Fighter development checkout")
    game = (Path(data) / "extracted").resolve()
    require(game.is_dir(), "Choose the data directory containing extracted game assets")
    workspace.mkdir(parents=True, exist_ok=True)
    identity, meta = project["identity"], project["metadata"]
    pack_id, fighter_id = identity["pack"], identity["fighter"]
    with tempfile.TemporaryDirectory(prefix="caf-export-", dir=workspace) as temporary:
        root = Path(temporary) / pack_id
        root.mkdir()
        import copy
        fighter = copy.deepcopy(project["fighter"])
        from . import outfits
        views = [(row, outfits.view(project, row["id"])) for row in outfits.entries(project)]
        def write_atlases(view, relative):
            result = {}
            if not view.get("textures", {}).get("atlases"):
                return result
            folder = root / relative
            folder.mkdir(parents=True)
            for slot, value in view["textures"]["atlases"].items():
                png = atlas_bytes(value)
                (folder / (slot + ".png")).write_bytes(png)
                result[slot] = {"path": relative + "/" + slot + ".png", "sha256": hashlib.sha256(png).hexdigest()}
            return result
        default_atlases = write_atlases(views[0][1], "atlases")
        if default_atlases:
            fighter["atlases"] = default_atlases
        if project["schema"] == SCHEMA3:
            fighter["outfit_name"] = project["outfit_name"]
            fighter["outfits"] = []
            for row, view in views[1:]:
                entry = dict(id=row["id"], name=row["name"],
                             **{key: copy.deepcopy(view["fighter"][key]) for key in outfits.APPEARANCE})
                atlases = write_atlases(view, "outfits/" + row["id"] + "/atlases")
                if atlases:
                    entry["atlases"] = atlases
                fighter["outfits"].append(entry)
        recipe = (json.dumps(fighter, sort_keys=True, indent=2) + "\n").encode()
        (root / "fighter.json").write_bytes(recipe)
        capability = "caf-fighter-3" if project["schema"] == SCHEMA3 else "caf-fighter-2" if project["schema"] == SCHEMA2 else "caf-fighter-1"
        manifest = {"schema": "fighter-registry-draft-1", "id": pack_id, "version": meta["version"],
                    "requires": {}, "resources": [{"id": "caf", "kind": "caf", "compatibility": {},
                    "source": {"format": capability, "selection": {"path": "fighter.json", "sha256": hashlib.sha256(recipe).hexdigest()}}}],
                    "fighters": [{"id": fighter_id, "name": meta["name"], "inherits": meta["donor"],
                                  "components": {"caf": pack_id + "/caf"}}], "overrides": []}
        for row, view in views:
            if "portrait" not in view:
                continue
            is_default = row["id"] == outfits.DEFAULT
            relative = "portraits" if is_default else "portraits/" + row["id"]
            png = Path(temporary) / ("portrait-" + row["id"] + ".png")
            png.write_bytes(portrait_bytes(view["portrait"]))
            portrait = contract(runtime, ["export-caf-portrait", "--game", str(game), "--portrait-png", str(png),
                                         "--portrait-out", str(root / relative)], temporary, workspace)
            source = portrait["source"]
            for key, descriptor in source.items():
                if isinstance(descriptor, dict):
                    descriptor["path"] = relative + "/" + descriptor["path"]
            portrait_id = "portrait" if is_default else "portrait-outfit-" + hashlib.sha256(row["id"].encode()).hexdigest()[:12]
            manifest["resources"].append({"id": portrait_id, "kind": "portrait", "compatibility": {}, "source": source})
            if is_default:
                manifest["fighters"][0]["components"]["portrait"] = pack_id + "/" + portrait_id
            if project["schema"] == SCHEMA3:
                fighter.setdefault("portraits", {})[row["id"]] = pack_id + "/" + portrait_id
        # Outfit portrait references are part of the hash-bound CAF recipe.
        recipe = (json.dumps(fighter, sort_keys=True, indent=2) + "\n").encode()
        (root / "fighter.json").write_bytes(recipe)
        manifest["resources"][0]["source"]["selection"]["sha256"] = hashlib.sha256(recipe).hexdigest()
        (root / "fighters.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        portrait_note = "Authored outfit portraits/thumbnails use the project's PNGs, converted through original UI templates." if any('portrait' in view for _, view in views) else "Portraits/thumbnails inherit the presentation donor."
        extras_note = ("Atlas and finisher overrides require the runtime's hash-checked fighter-caf-extras.bin support.\n"
                       "Declared native atlases replace RGB only; original material alpha is retained.\n"
                       "Saved finisher identities resolve against the player's original database.\n") if capability != "caf-fighter-1" else ""
        if capability == "caf-fighter-3":
            extras_note += "One roster entry exposes up to three outfits through the native clothing selector.\nCombat settings are shared; appearance, atlases and portraits are outfit-specific.\n"
        (root / "README.md").write_text(f"# {meta['name']}\n\n{meta['description']}\n\nAuthor: {meta['author'] or 'Unspecified'}\nVersion: {meta['version']}\n\nRequires Custom Fighter runtime with {capability} support.\n{extras_note}CAF appearance, training stats and retail style combination come from fighter.json.\nVoice, AI and inherited presentation use {meta['donor']}.\n{portrait_note}\nNo Story save or currency is included. The player's own game files supply the CAF parts.\n", encoding="utf-8")
        (root / "LICENSE.txt").write_text(meta["license"] or "No additional license granted. Original game assets are supplied locally by the player.\n", encoding="utf-8")
        progress("Validating the complete fighter pack against your game files…")
        report = contract(runtime, ["validate", "--pack", str(root), "--game", str(game)], temporary, workspace)
        require(report.get("ok") is True and report.get("native_compilation") is True, "Runtime did not confirm complete native compilation")
        # The shared inventory is validated by fighter-contract, not a second
        # workshop-specific package format. Publish only after it succeeds.
        destination.parent.mkdir(parents=True, exist_ok=True)
        created = False
        try:
            with destination.open("xb") as stream:
                created = True
                with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for path in sorted(root.rglob("*")):
                        if path.is_file():
                            archive.write(path, pack_id + "/" + path.relative_to(root).as_posix())
        except Exception:
            if created:
                destination.unlink(missing_ok=True)
            raise
        return report
