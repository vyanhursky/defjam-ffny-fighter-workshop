"""Local read-only profile inspector."""
import argparse
import json
from pathlib import Path

from .container import SaveError
from .profiles import discover


def main(argv=None):
    parser = argparse.ArgumentParser(prog="defjam-caf")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Validate and list profiles without changing them")
    inspect.add_argument("--data", type=Path, required=True)
    create = commands.add_parser("project", help="Create a standalone fighter project from an existing profile")
    create.add_argument("--data", type=Path, required=True)
    create.add_argument("--profile", required=True)
    create.add_argument("--out", type=Path, required=True)
    export = commands.add_parser("export-mod", help="Validate and export a Custom Fighter Mod from a project")
    export.add_argument("project", type=Path)
    export.add_argument("--data", type=Path, required=True)
    export.add_argument("--runtime", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)
    export.add_argument("--workspace", type=Path, required=True)
    atlas = commands.add_parser("import-atlas", help="Embed a native RGB atlas in a new versioned fighter project")
    atlas.add_argument("project", type=Path)
    atlas.add_argument("--slot", choices=("a", "b", "c", "d", "d1", "d2"), required=True)
    atlas.add_argument("--png", type=Path, required=True)
    atlas.add_argument("--out", type=Path, required=True)
    for command in ("inspect-ps2-caf", "import-ps2-caf"):
        ps2 = commands.add_parser(command, help="Experimental read-only CAF recovery from a PCSX2 snapshot or mod ZIP")
        ps2.add_argument("source", type=Path)
        ps2.add_argument("--name", required=True, help="Exact uppercase PS2 profile name")
        ps2.add_argument("--data", type=Path, required=command == "import-ps2-caf")
        if command == "import-ps2-caf":
            ps2.add_argument("--out", type=Path, required=True)
            ps2.add_argument("--donor", default="retail/blaze", help="Explicit retail voice/AI/presentation donor")
    args = parser.parse_args(argv)
    try:
        if args.command == "import-atlas":
            from .projects import read, write, with_atlas
            from .profiles import read_bounded
            document = with_atlas(read(args.project)[0], args.slot, read_bounded(args.png, 1024 * 1024))
            write(args.out, document)
            print(json.dumps({"project": str(args.out), "atlas": args.slot, "material_alpha": "native-original", "native_playtest": False}))
            return 0
        if args.command in ("inspect-ps2-caf", "import-ps2-caf"):
            from . import pcsx2
            report = pcsx2.inspect(args.source, args.name, args.data)
            if args.command == "import-ps2-caf":
                from .projects import write
                write(args.out, pcsx2.project(report, args.donor))
                report["project"] = str(args.out)
            print(json.dumps(report, indent=2))
            return 0
        if args.command == "project":
            from .projects import from_profile, write
            from .assets import Database
            selected = next((p for p in discover(args.data).profiles if p.name == args.profile), None)
            if selected is None:
                raise SaveError("Requested profile is unavailable")
            database = Database(args.data / "extracted") if (args.data / "extracted").is_dir() else None
            write(args.out, from_profile(selected.container.payload, selected.name, database))
            print(json.dumps({"project": str(args.out), "story_progress_included": False}))
            return 0
        if args.command == "export-mod":
            from .projects import read
            from .fighter_mod import export_mod
            print(json.dumps(export_mod(read(args.project)[0], args.out, args.runtime, args.data, args.workspace), indent=2))
            return 0
        result = discover(args.data)
    except (SaveError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps({"title_root": str(result.title_root), "profiles": [
        {"name": p.name, "path": str(p.path), "directory_kind": p.directory_kind,
         "sha256": p.sha256, "extra_files": p.extra_files,
         "unchanged_roundtrip": p.container.encode() == p.path.read_bytes()}
        for p in result.profiles], "issues": result.issues}, indent=2))
    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
