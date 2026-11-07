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
    args = parser.parse_args(argv)
    try:
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
