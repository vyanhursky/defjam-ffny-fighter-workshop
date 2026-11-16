"""Folders the player chose once, kept between launches: the Recomp data directory and the runtime checkout.

Stored in the Workshop's own workspace, never next to a save. A remembered folder is only offered again while it still
passes its check (the data folder still holds extracted game files, the runtime still has its tools), so a moved or
deleted folder simply falls back to asking."""

import json
from pathlib import Path

from .storage import atomic_bytes
from .diagnostics import log_detail

FILE = "remembered.json"
KEYS = ("data", "runtime", "app")
_reported = set()
_pending = {}


def _read(workspace):
    path = Path(workspace) / FILE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Remembered settings must be an object")
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        key = str(path.resolve())
        try:
            stamp = (key, path.stat().st_mtime_ns, path.stat().st_size)
        except OSError:
            stamp = (key, None, None)
        if stamp not in _reported:
            _reported.add(stamp)
            _pending[key] = "Your remembered folders could not be read; choose them again."
            log_detail(workspace, f"Remembered settings could not be read: {exc}")
        return {}
    return value


def take_warning(workspace):
    return _pending.pop(str((Path(workspace) / FILE).resolve()), None)


def runtime_ok(path):
    """Any game version or checkout that has the contract script; what it can do is runtimes.inspect's business."""
    return (Path(path) / "scripts/fighter-contract.py").is_file()


def app_ok(path):
    return Path(path).is_dir()


def data_ok(path):
    return (Path(path) / "extracted").is_dir()


CHECKS = {"data": data_ok, "runtime": runtime_ok, "app": app_ok}


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


RECENT_LIMIT = 6
RECENT_MODES = ("caf", "retail-new", "retail-edit")


def recents(workspace):
    """Projects opened or saved lately, newest first, without the ones that no longer exist."""
    rows = _read(workspace).get("recent")
    out = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("mode") in RECENT_MODES and isinstance(row.get("path"), str):
            try:
                if Path(row["path"]).is_file():
                    out.append(
                        dict(mode=row["mode"], path=row["path"], name=str(row.get("name") or Path(row["path"]).stem))
                    )
            except OSError:
                pass
    return out[:RECENT_LIMIT]


def add_recent(workspace, mode, path, name=None):
    """Put a project at the top of the Home list. Never raises: a list that cannot be saved is only a convenience lost."""
    if mode not in RECENT_MODES:
        return False
    path = str(Path(path).resolve())
    try:
        value = _read(workspace)
        rows = [r for r in recents(workspace) if r["path"] != path]
        value["recent"] = [dict(mode=mode, path=path, name=name or Path(path).stem)] + rows[: RECENT_LIMIT - 1]
        Path(workspace).mkdir(parents=True, exist_ok=True)
        atomic_bytes(Path(workspace) / FILE, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except OSError:
        return False
    return True


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
