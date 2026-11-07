"""Atomic persistence, stale-source detection and bounded full-profile archives."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import zipfile

from .container import Container, MAX_SAVE_SIZE, SaveError
from .fields import renamed
from .profiles import Profile, directory_name, metadata_name, read_bounded, TITLE_ID, PROFILE_SIZE


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".caf-write-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def atomic_json(path, data):
    atomic_bytes(path, json.dumps(data, indent=2, allow_nan=False).encode("utf-8"))


@contextmanager
def writer_lock(folder):
    lock = Path(folder) / ".caf-editor.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"0")
        os.lseek(descriptor, 0, os.SEEK_SET)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SaveError("Another editor is writing this profile") from exc
        yield
    finally:
        # Closing releases the kernel lock even after a process crash. Retain
        # the tiny lock file so another writer cannot lock a different inode.
        os.close(descriptor)


def current_bytes(profile):
    raw = read_bounded(profile.path, MAX_SAVE_SIZE)
    if sha(raw) != profile.sha256:
        raise SaveError("The profile changed on disk. Reload it before saving")
    metadata = read_bounded(profile.path.parent / "SaveMeta.xbx", 4096)
    if metadata_name(metadata) != profile.name:
        raise SaveError("The profile identity changed on disk. Reload it")
    return raw


def profile_files(profile, save):
    current_bytes(profile)
    files = {}
    for path in profile.path.parent.iterdir():
        if path.name == ".caf-editor.lock":
            continue
        if not re.fullmatch(r"[A-Za-z0-9 _.-]{1,128}", path.name) or path.name in {".", ".."}:
            raise SaveError("Unsupported file in profile folder")
        files[path.name] = read_bounded(path, MAX_SAVE_SIZE)
    if len(files) > 32 or sum(map(len, files.values())) > 8 * 1024 * 1024:
        raise SaveError("Profile folder exceeds the transfer limit")
    files[profile.path.name] = save.encode()
    return files


def archive_bytes(profile, save):
    import io
    files = profile_files(profile, save)
    manifest = {"schema": 1, "title": TITLE_ID, "name": profile.name,
                "files": {name: {"sha256": sha(raw), "size": len(raw)} for name, raw in files.items()}}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
        for name, raw in files.items():
            archive.writestr("profile/" + name, raw)
    return output.getvalue()


def export_profile(profile, save, destination):
    destination = Path(destination)
    if destination.exists():
        raise SaveError("Export destination already exists")
    raw = archive_bytes(profile, save)
    # Exclusive creation never overwrites an existing export.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def read_archive(path):
    import io
    raw = read_bounded(Path(path), 8 * 1024 * 1024)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 33 or len({i.filename for i in infos}) != len(infos) or sum(i.file_size for i in infos) > 8 * 1024 * 1024:
            raise SaveError("Invalid or oversized profile archive")
        if any(i.flag_bits & 1 or i.file_size > MAX_SAVE_SIZE for i in infos):
            raise SaveError("Encrypted or oversized archive member")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema") != 1 or manifest.get("title") != TITLE_ID:
            raise SaveError("Unsupported profile archive")
        files = {}
        records = manifest.get("files", {})
        if not isinstance(records, dict) or not records:
            raise SaveError("Missing profile archive files")
        if len({name.casefold() for name in records}) != len(records):
            raise SaveError("Case-colliding profile archive filenames")
        expected = {"manifest.json"}
        for name, record in records.items():
            if not re.fullmatch(r"[A-Za-z0-9 _.-]{1,128}", name) or name in {".", "..", ".caf-editor.lock"}:
                raise SaveError("Unsafe archive member name")
            expected.add("profile/" + name)
            data = archive.read("profile/" + name)
            if record != {"sha256": sha(data), "size": len(data)}:
                raise SaveError("Profile archive checksum mismatch")
            files[name] = data
        if {i.filename for i in infos} != expected:
            raise SaveError("Unexpected profile archive contents")
        name = metadata_name(files["SaveMeta.xbx"])
        save = Container.read(files[name])
        if name == "Options" or len(save.metadata) != 64 or len(save.payload) != PROFILE_SIZE:
            raise SaveError("Archive does not contain a supported fighter profile")
        if name != manifest.get("name") or save.payload[:16].split(b"\0", 1)[0].decode("ascii") != name:
            raise SaveError("Profile archive identity mismatch")
        return name, save, files


def install_files(title, name, files):
    title = Path(title)
    if title.name != TITLE_ID or title.is_symlink():
        raise SaveError("Choose a regular FFNY title-save folder")
    title.mkdir(parents=True, exist_ok=True)
    canonical, legacy = directory_name(name), directory_name(name, legacy=True)
    if (title / canonical).exists() or (title / legacy).exists():
        raise SaveError("A profile with this identity already exists")
    stage = title / (".caf-import-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        for filename, raw in files.items():
            (stage / filename).write_bytes(raw)
        # Reserve identity to prevent two editors installing the same name.
        with writer_lock(title):
            if (title / canonical).exists() or (title / legacy).exists():
                raise SaveError("A profile with this identity already exists")
            stage.rename(title / canonical)
    finally:
        if stage.exists():
            # Only this function's new, enumerated staging files may be removed.
            for path in stage.iterdir():
                path.unlink()
            stage.rmdir()
    return title / canonical / name


def duplicate(profile, save, name):
    save = renamed(save, name)
    files = profile_files(profile, save)
    files.pop(profile.name)
    files[name] = save.encode()
    files["SaveMeta.xbx"] = ("Name=" + name + "\r\n").encode("utf-16-le")
    files["SaveMeta.xbx"] = b"\xff\xfe" + files["SaveMeta.xbx"]
    return install_files(profile.path.parent.parent, name, files)


def save_profile(profile, save, backup_root):
    Container.read(save.encode())
    with writer_lock(profile.path.parent):
        original = current_bytes(profile)
        backup_root = Path(backup_root)
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = backup_root / f"{stamp}-{profile.name}-{uuid.uuid4().hex[:8]}.djprofile"
        export_profile(profile, Container.read(original), backup)
        # Recheck immediately before replacing, after the backup is durable.
        current_bytes(profile)
        atomic_bytes(profile.path, save.encode())
        return backup
