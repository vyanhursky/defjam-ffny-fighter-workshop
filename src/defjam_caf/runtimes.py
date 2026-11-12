"""Which installed game version (or source checkout) the Workshop talks to, and what each one can do.

The Workshop's mod, voice, animation and retail tools run scripts that ship with the game. Older game versions lack some
of them, so every candidate is inspected by reading its files (never by running it) and reported feature by feature.
A game folder holds one or more versions under ``app/versions/<version>/source``; a developer checkout is a single
``scripts/fighter-contract.py`` tree."""
import json
import os
import re
import sys
from pathlib import Path

CONTRACT = Path("scripts/fighter-contract.py")
COMMANDS = re.compile(r"add_argument\(\s*['\"]command['\"]\s*,\s*choices\s*=\s*[\(\[]([^\)\]]*)[\)\]]", re.S)
FORMAT = re.compile(r"^FORMAT\s*=\s*['\"]([^'\"]+)['\"]", re.M)
VERSION_DIR = re.compile(r"^(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)[0-9A-Za-z.]*?)?)-([0-9a-f]{7,40})(?:-|$)")

# What each part of the Workshop needs from a game version: contract commands, and whether it must understand the
# Custom Fighter recipe format the Workshop writes.
FEATURES = (
    ("export", "Export fighter mods", ("validate",), True,
     "Needs a game version that understands Custom Fighter mods."),
    ("tools", "Voice, entrance and AI tools", ("workshop-catalog", "workshop-check", "workshop-audio", "workshop-animation"),
     False, "Needs a game version with the Workshop tool commands."),
    ("menu", "Retail menu artwork import", ("export-ui-reference",), False,
     "Needs a game version with retail UI reference export."),
    ("retail", "Retail fighter studio", ("catalog", "export-retail-appearance", "preview-fighter", "validate"), False,
     "Needs a game version with retail appearance export."),
)
_cache = {}


def default_folder(*, platform=None, home=None, environ=None):
    """The folder the Recomp app installs into, when it exists: it holds both the game data and the app versions."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == "win32":
        base = Path(environ["LOCALAPPDATA"]) if environ.get("LOCALAPPDATA") else home / "AppData/Local"
        folder = base / "DefJamRecompiled"
    elif platform == "darwin":
        folder = home / "Library/Application Support/DefJamRecompiled"
    else:
        return None
    return folder if folder.is_dir() else None


def _read(path, limit=4_000_000):
    try:
        with open(path, "rb") as stream:
            return stream.read(limit).decode("utf-8", "replace")
    except OSError:
        return ""


def inspect(path, recipe_format):
    """What one candidate offers. path is the folder that contains scripts/fighter-contract.py."""
    path = Path(path)
    contract = path / CONTRACT
    try:
        stamp = (contract.stat().st_mtime_ns, (path / "setup/fighter_caf.py").stat().st_mtime_ns
                 if (path / "setup/fighter_caf.py").is_file() else 0)
    except OSError:
        stamp = None
    key = (str(path), stamp, recipe_format)
    if stamp is not None and key in _cache:
        return _cache[key]
    match = COMMANDS.search(_read(contract))
    commands = sorted(set(re.findall(r"['\"]([a-z][a-z0-9-]*)['\"]", match.group(1)))) if match else []
    declared = FORMAT.search(_read(path / "setup/fighter_caf.py"))
    caf_format = declared.group(1) if declared else None
    features, missing = {}, {}
    for name, label, needs, needs_format, why in FEATURES:
        lacks = [c for c in needs if c not in commands]
        if needs_format and caf_format != recipe_format:
            lacks.append("the " + recipe_format + " fighter format" + (" (this version uses " + caf_format + ")" if caf_format else ""))
        features[name] = not lacks
        if lacks:
            missing[name] = why
    row = dict(path=str(path), commands=commands, format=caf_format, features=features, missing=missing,
               usable=bool(commands), complete=all(features.values()),
               labels={name: label for name, label, *_ in FEATURES})
    if stamp is not None:
        _cache[key] = row
    return row


def _installed_version(folder):
    """The app's own record of the version it runs, when the folder is the Recomp app folder."""
    try:
        record = json.loads((Path(folder) / "app/installed.json").read_text(encoding="utf-8"))
        return record.get("version"), Path(record.get("source", "")).resolve() if record.get("source") else None
    except (OSError, ValueError, AttributeError):
        return None, None


def _label(name):
    match = VERSION_DIR.match(name)
    return match.group(1) if match else name


def scan(folder, recipe_format):
    """Candidates found under a folder the player picked. The folder may be the Recomp app folder, its app/versions
    folder, one version, or a source checkout."""
    folder = Path(folder)
    found, seen = [], set()

    def add(source, label, note):
        resolved = str(source.resolve())
        if resolved in seen or not (source / CONTRACT).is_file():
            return
        seen.add(resolved)
        row = inspect(source, recipe_format)
        row.update(label=label, note=note)
        found.append(row)

    current_version, current_source = _installed_version(folder)
    for versions in (folder / "app/versions", folder / "versions", folder):
        if not versions.is_dir():
            continue
        for child in sorted(versions.iterdir(), key=lambda p: p.name):
            source = child / "source"
            if source.is_dir() and VERSION_DIR.match(child.name):
                installed = current_source is not None and source.resolve() == current_source
                add(source, "Game " + _label(child.name), "installed" if installed else "")
    add(folder / "source", "Game (source folder)", "")
    add(folder, "Source checkout", "developer checkout")

    def order(row):
        version = re.match(r"Game (\d+)\.(\d+)\.(\d+)", row["label"])
        return (0 if version else 1, tuple(-int(v) for v in version.groups()) if version else (0, 0, 0), row["label"])

    found.sort(key=order)
    data = next((p for p in (folder / "data", folder) if (p / "extracted").is_dir()), None)
    return dict(folder=str(folder), candidates=found, data=str(data) if data else None, current=current_version)


def describe(path, recipe_format):
    """A short label for the selected runtime, shown in the header."""
    if path is None:
        return None
    row = inspect(path, recipe_format)
    parent = Path(path).parent.name
    version = VERSION_DIR.match(parent)
    row["label"] = ("Game " + _label(parent)) if version and Path(path).name == "source" else Path(path).name or str(path)
    return row


def require(path, feature, recipe_format):
    """Raise a plain-language error when the chosen game version cannot do something the player asked for."""
    from .container import SaveError
    if path is None:
        raise SaveError("Game setup needed: choose your game version first (Game setup, top right).")
    row = describe(path, recipe_format)
    if not row["usable"]:
        raise SaveError("This folder does not look like a game version: scripts/fighter-contract.py is missing. "
                        "Choose another in Game setup.")
    if not row["features"].get(feature):
        label = row["labels"][feature]
        raise SaveError(label + " is not available in " + row["label"] + ". " + row["missing"][feature]
                        + " Choose a newer version in Game setup.")
    return row
