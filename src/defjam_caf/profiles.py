"""Read-only discovery by exact metadata and signed profile identity."""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re

from .container import Container, MAX_SAVE_SIZE, SaveError

TITLE_ID = "45410049"
PROFILE_SIZE = 0x5904


def directory_name(name: str, *, legacy: bool = False) -> str:
    value = 0
    units = name.encode("utf-16-le", errors="strict")
    for i in range(0, len(units), 2):
        value = (value * 65536 + int.from_bytes(units[i:i + 2], "little")) % (2**48 - 59)
    result = f"{value:012X}"
    if legacy:
        result = result[:-1] + f"{(value | (value >> 32)) & 15:X}"
    return result


def metadata_name(raw: bytes) -> str:
    if not 2 <= len(raw) <= 4096 or not raw.startswith(b"\xff\xfe") or len(raw) % 2:
        raise SaveError("Profile metadata must be bounded UTF-16LE with a BOM")
    try:
        names = [line[5:] for line in raw.decode("utf-16").splitlines() if line.startswith("Name=")]
    except UnicodeError as exc:
        raise SaveError("Invalid profile metadata encoding") from exc
    if len(names) != 1 or not re.fullmatch(r"[A-Za-z0-9 _-]{1,128}", names[0]):
        raise SaveError("Missing, ambiguous or unsupported profile name")
    return names[0]


def read_bounded(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise SaveError("Expected a regular file, without a symbolic link")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise SaveError("File exceeds the supported size limit")
    return raw


@dataclass(frozen=True)
class Profile:
    name: str
    path: Path
    directory_kind: str
    sha256: str
    container: Container = field(repr=False)
    extra_files: tuple[str, ...] = ()


@dataclass
class Discovery:
    title_root: Path
    profiles: list[Profile] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)


def title_root(data: Path) -> Path:
    data = Path(data).expanduser().resolve()
    candidates = (data / "save" / "UserData" / TITLE_ID, data / "UserData" / TITLE_ID,
                  data / TITLE_ID, data)
    for path in candidates:
        if path.is_dir() and path.name.upper() == TITLE_ID:
            # Reject linked children rather than following them into another save root.
            relative = path.relative_to(data)
            current = data
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    raise SaveError("Save directories must not be symbolic links")
            return path
    raise SaveError("No FFNY title saves found; select the Recomp data or save directory")


def discover(data: Path) -> Discovery:
    root = title_root(data)
    result = Discovery(root)
    folders = sorted(root.iterdir(), key=lambda p: p.name)
    identities = [p.name.upper() for p in folders]
    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            if folder.is_symlink() or not re.fullmatch(r"[0-9A-Fa-f]{12}", folder.name):
                raise SaveError("Unexpected or linked profile directory")
            if identities.count(folder.name.upper()) > 1:
                raise SaveError("Case-colliding profile directories")
            name = metadata_name(read_bounded(folder / "SaveMeta.xbx", 4096))
            canonical, legacy = directory_name(name), directory_name(name, legacy=True)
            if folder.name.upper() == canonical:
                kind = "canonical"
            elif folder.name.upper() == legacy and canonical not in identities:
                kind = "legacy"
            else:
                raise SaveError("Folder identity does not match the profile metadata")
            raw = read_bounded(folder / name, MAX_SAVE_SIZE)
            save = Container.read(raw)
            if name == "Options":
                continue
            if len(save.metadata) != 64 or len(save.payload) != PROFILE_SIZE:
                raise SaveError("Unsupported character profile layout")
            field_name = save.payload[:16].split(b"\0", 1)[0]
            try:
                actual_name = field_name.decode("ascii")
            except UnicodeError as exc:
                raise SaveError("Unsupported character profile name encoding") from exc
            if actual_name != name or b"\0" not in save.payload[:16]:
                raise SaveError("Profile payload name disagrees with its metadata")
            extras = tuple(sorted(p.name for p in folder.iterdir()
                                  if p.name not in {name, "SaveMeta.xbx", "saveimage.xbx", ".caf-editor.lock"}))
            result.profiles.append(Profile(name, folder / name, kind,
                                           hashlib.sha256(raw).hexdigest(), save, extras))
        except (SaveError, OSError, UnicodeError) as exc:
            result.issues.append({"directory": folder.name, "error": str(exc)})
    return result
