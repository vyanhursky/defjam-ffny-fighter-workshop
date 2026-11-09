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
    args = parser.parse_args(argv)
    try:
        if args.command == "project":
            from .projects import from_fields, write
            from .fields import read_fields
            selected = next((p for p in discover(args.data).profiles if p.name == args.profile), None)
            if selected is None:
                raise SaveError("Requested profile is unavailable")
            write(args.out, from_fields(read_fields(selected.container.payload), selected.name))
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
