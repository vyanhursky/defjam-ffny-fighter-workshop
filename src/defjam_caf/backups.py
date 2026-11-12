"""The backups made before each profile save, and putting one back.

A backup is an ordinary exported profile archive in the Workshop's own workspace. Restoring one replaces the profile's
save file with the archived one, after first making a backup of the save it replaces, so a restore can be undone the
same way."""
import re
from datetime import datetime, timezone
from pathlib import Path

from .container import SaveError
from .storage import read_archive, save_profile

NAME = re.compile(r"^(\d{8}T\d{6})-(.+)-([0-9a-f]{8})\.djprofile$")
SHOWN = 20


def entries(root, profile_name):
    """Backups of one profile, newest first: id (the file name), when (ISO, UTC) and size in bytes."""
    root = Path(root)
    if not root.is_dir():
        return []
    rows = []
    for path in root.iterdir():
        match = NAME.match(path.name)
        if not match or match.group(2) != profile_name or path.is_symlink() or not path.is_file():
            continue
        try:
            when = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        rows.append(dict(id=path.name, when=when.isoformat(), size=path.stat().st_size))
    return sorted(rows, key=lambda row: row["id"], reverse=True)[:SHOWN]


def restore(profile, root, backup_id):
    """Replace the profile's save with the one in a backup. Returns the backup made of the save it replaced."""
    if not isinstance(backup_id, str) or Path(backup_id).name != backup_id or not NAME.match(backup_id):
        raise SaveError("Choose one of the listed backups")
    path = Path(root) / backup_id
    if path.is_symlink() or not path.is_file():
        raise SaveError("That backup no longer exists")
    name, save, _ = read_archive(path)
    if name != profile.name:
        raise SaveError("That backup belongs to a different profile")
    return save_profile(profile, save, root)
