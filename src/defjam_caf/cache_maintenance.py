"""Retention of owned wardrobe caches; backups/projects and unknown files are excluded."""

from functools import lru_cache
import os
from pathlib import Path
import re
import shutil
import stat

from .container import SaveError

IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
INCOMPLETE = re.compile(r"incomplete-[0-9a-f]{32}\Z")


def redirected(path):
    try:
        return path.is_symlink() or bool(
            getattr(path.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return True


def root_for(workspace):
    workspace = Path(workspace).resolve()
    root = workspace / "assets"
    if root.exists() and (redirected(root) or not root.resolve().is_relative_to(workspace)):
        raise SaveError("The private cache folder is redirected. Choose another Workshop workspace before clearing it.")
    return root


def remove_owned(path, root):
    # Validate the final absolute target before every recursive deletion.
    resolved, expected = path.resolve(), root.resolve()
    if redirected(path) or resolved == expected or not resolved.is_relative_to(expected):
        raise SaveError("Cache cleanup refused a redirected folder.")
    for directory, dirs, files in os.walk(path, followlinks=False):
        if any(redirected(Path(directory) / name) for name in [*dirs, *files]):
            raise SaveError("Cache cleanup refused a redirected file or folder.")
    shutil.rmtree(resolved)


def identities(root):
    return (
        [p for p in root.iterdir() if IDENTITY.fullmatch(p.name) and p.is_dir() and not redirected(p)]
        if root.is_dir()
        else []
    )


def prune(workspace, active):
    root = root_for(workspace)
    active = Path(active).resolve()
    if active.parent != root.resolve() or not IDENTITY.fullmatch(active.name):
        raise SaveError("Cache identity leaves the private workspace.")
    completed = []
    for identity in identities(root):
        for child in identity.iterdir():
            if INCOMPLETE.fullmatch(child.name) and child.is_dir() and not redirected(child):
                remove_owned(child, root)
        catalog = identity / "catalog/catalog.json"
        if catalog.is_file() and not redirected(catalog):
            completed.append((catalog.stat().st_mtime_ns, identity))
    keep = {active}
    for _, identity in sorted(completed, key=lambda row: row[0], reverse=True):
        if len(keep) < 2:
            keep.add(identity.resolve())
    for _, identity in completed:
        if identity.resolve() not in keep:
            remove_owned(identity, root)
    _info.cache_clear()


def clear(workspace):
    root = root_for(workspace)
    for identity in identities(root):
        remove_owned(identity, root)
    _info.cache_clear()


@lru_cache(maxsize=8)
def _info(workspace):
    root = root_for(workspace)
    size = 0
    for identity in identities(root):
        for directory, dirs, files in os.walk(identity, followlinks=False):
            dirs[:] = [d for d in dirs if not redirected(Path(directory) / d)]
            for name in files:
                path = Path(directory) / name
                if not redirected(path):
                    size += path.stat().st_size
    return dict(path=str(root), bytes=size)


def info(workspace):
    try:
        return dict(_info(str(Path(workspace).resolve())))
    except (OSError, SaveError) as exc:
        return dict(path=str(Path(workspace) / "assets"), bytes=None, error=str(exc))
