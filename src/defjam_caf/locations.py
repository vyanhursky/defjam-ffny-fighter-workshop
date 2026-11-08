"""Recomp's native data defaults, separate from the editor's workspace."""
from pathlib import Path
import sys

from .container import SaveError
from .profiles import title_root


def default_data_directory(*, platform=None, home=None):
    platform = sys.platform if platform is None else platform
    if platform == "darwin":
        # Matches both setup/macos/Setup/main.swift and app::default_locations.
        return (Path.home() if home is None else Path(home)) / "Library/Application Support/DefJamRecompiled/data"
    return None


def initial_data_directory(explicit=None, *, platform=None, home=None):
    if explicit is not None:
        return Path(explicit).expanduser()
    default = default_data_directory(platform=platform, home=home)
    if default is not None:
        try:
            title_root(default)
        except (OSError, SaveError):
            return None
        return default
    return None
