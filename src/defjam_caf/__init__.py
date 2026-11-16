"""Offline Def Jam FFNY Recomp CAF/profile tools."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib

try:
    __version__ = version("defjam-ffny-fighter-workshop")
except PackageNotFoundError:
    # An uninstalled source checkout has no distribution metadata. Frozen builds
    # carry that metadata explicitly (see package_desktop.py).
    try:
        __version__ = tomllib.loads(
            (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
    except (OSError, KeyError, ValueError):
        __version__ = "0+unknown"
