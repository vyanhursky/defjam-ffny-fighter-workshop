"""Folders the player chose once, kept between launches: the Recomp data directory and the runtime checkout.

Stored in the Workshop's own workspace, never next to a save. A remembered folder is only offered again while it still
passes its check (the data folder still holds extracted game files, the runtime still has its tools), so a moved or
deleted folder simply falls back to asking."""
import json
from pathlib import Path

from .storage import atomic_bytes

FILE = "remembered.json"
KEYS = ("data", "runtime")


def _read(workspace):
    try:
        value = json.loads((Path(workspace) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def runtime_ok(path):
    path = Path(path)
    return (path / "setup/fighter_caf.py").is_file() and (path / "scripts/fighter-contract.py").is_file()


def data_ok(path):
    return (Path(path) / "extracted").is_dir()


CHECKS = {"data": data_ok, "runtime": runtime_ok}


def recall(workspace, key):
    """The remembered folder for key, or None when nothing is remembered or it no longer qualifies."""
    assert key in KEYS
    stored = _read(workspace).get(key)
    if not isinstance(stored, str) or not stored:
        return None
    path = Path(stored)
    try:
        return path if CHECKS[key](path) else None
    except OSError:
        return None


def remember(workspace, key, path):
    """Remember a folder that passes its check. Anything else is ignored, so a wrong pick is never offered again."""
    assert key in KEYS
    path = Path(path).resolve()
    try:
        if not CHECKS[key](path):
            return False
        value = _read(workspace)
        value[key] = str(path)
        Path(workspace).mkdir(parents=True, exist_ok=True)
        atomic_bytes(Path(workspace) / FILE, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except OSError:
        return False
    return True
