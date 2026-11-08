"""Build a game-free native desktop package; run on each target OS/CPU."""
import argparse
import hashlib
import os
from importlib.metadata import distributions, version
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

NAME = "defjam-ffny-fighter-workshop"
BUNDLE_ID = "org.ffnycommunity.fighterworkshop"


def collect_notices(root, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY.md", "README.md", "PROGRESS.md"):
        shutil.copy2(root / name, destination / name)
    for name in ("beta-test-guide.md", "validation.md", "desktop-platforms.md"):
        shutil.copy2(root / "docs" / name, destination / name)
    shutil.copytree(root / "docs", destination / "docs")
    notices = destination / "dependency-licenses"
    notices.mkdir()
    wanted = {"pyside6", "pyside6_essentials", "pyside6_addons", "pyside6_webengine", "pyside6_pdf",
              "shiboken6", "pillow", "numpy", "pyinstaller"}
    for package in distributions():
        name = package.metadata["Name"]
        if name.lower().replace("-", "_") not in wanted:
            continue
        for file in package.files or []:
            if "/licenses/" in str(file).replace("\\", "/").lower() or file.name.lower().startswith(("license", "copying")):
                source = Path(package.locate_file(file))
                if source.is_file():
                    lower_parts = [part.lower() for part in file.parts]
                    relative = Path(*file.parts[lower_parts.index("licenses") + 1:]) if "licenses" in lower_parts else Path(file.name)
                    target = notices / name / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for python_license in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"):
        if python_license.is_file():
            shutil.copy2(python_license, notices / "Python-LICENSE.txt")
            break
    else:
        raise RuntimeError("Python LICENSE.txt not found in the build interpreter")


def archive_package(destination, system, machine, app_version):
    label = {"darwin": "macos", "win32": "windows", "linux": "linux"}[system]
    machine = {"aarch64": "arm64", "amd64": "x64", "x86_64": "x64"}.get(machine.lower(), machine.lower())
    base = destination.parent / f"{NAME}-{app_version}-{label}-{machine}"
    if system == "darwin":
        # ditto preserves the bundle's framework symlinks, modes and signatures.
        archive = Path(str(base) + ".zip")
        archive.unlink(missing_ok=True)
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(destination), str(archive)], check=True)
    elif system == "linux":
        archive = Path(str(base) + ".tar.gz")
        with tarfile.open(archive, "w:gz") as output:
            output.add(destination, arcname=destination.name)
    else:
        archive = Path(shutil.make_archive(str(base), "zip", destination.parent, destination.name))
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    Path(str(archive) + ".sha256").write_text(digest.hexdigest() + "  " + archive.name + "\n", encoding="utf-8")
    return archive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-archive", action="store_true", help="Only build the native app/folder")
    args = parser.parse_args(argv)
    if sys.platform not in {"win32", "darwin", "linux"}:
        parser.error("Build on Windows, macOS or Linux")
    root = Path(__file__).resolve().parents[1]
    (root / "build").mkdir(exist_ok=True)
    # Add notices before PyInstaller signs the macOS bundle. Never mutate a
    # signed .app afterwards, or ship the sibling intermediate onedir instead.
    with tempfile.TemporaryDirectory(prefix="package-notices-", dir=root / "build") as temporary:
        docs = Path(temporary) / "documentation"
        collect_notices(root, docs)
        command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                   "--name", NAME, "--paths", str(root / "src"),
                   "--add-data", f"{root / 'src/defjam_caf/resources'}:defjam_caf/resources",
                   "--add-data", f"{root / 'src/defjam_caf/_vendor/LICENSE'}:defjam_caf/_vendor",
                   "--add-data", f"{docs}:documentation"]
        icons = root / "src/defjam_caf/resources/branding"
        if sys.platform == "darwin":
            command += ["--osx-bundle-identifier", BUNDLE_ID, "--icon", str(icons / "defjam.icns")]
        elif sys.platform == "win32":
            command += ["--icon", str(icons / "defjam.ico")]
        command.append(str(root / "scripts/launch_desktop.py"))
        subprocess.run(command, cwd=root, check=True, env=dict(os.environ,
            PYINSTALLER_CONFIG_DIR=str(root / "build" / "pyinstaller-cache")))
        destination = root / "dist" / (NAME + (".app" if sys.platform == "darwin" else ""))
        if sys.platform != "darwin":
            shutil.copytree(docs, destination / "documentation", dirs_exist_ok=True)
    if sys.platform == "win32":
        print('After a build in a Low-integrity workspace, run in PowerShell:')
        print(f"icacls '{destination}' /setintegritylevel '(OI)(CI)M' /T /Q")
    print(destination, flush=True)
    if not args.no_archive:
        print(archive_package(destination, sys.platform, platform.machine(), version(NAME)), flush=True)


if __name__ == "__main__":
    main()
