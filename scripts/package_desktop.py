"""Build a game-free native desktop folder on the current platform."""
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", "defjam-ffny-caf-customizer", "--paths", str(root / "src"),
                    "--add-data", f"{root / 'src/defjam_caf/resources'}:defjam_caf/resources",
                    "--add-data", f"{root / 'src/defjam_caf/_vendor/LICENSE'}:defjam_caf/_vendor",
                    str(root / "scripts/launch_desktop.py")], cwd=root, check=True)
    destination = root / "dist" / "defjam-ffny-caf-customizer"
    for name in ("LICENSE", "THIRD_PARTY.md", "README.md"):
        shutil.copy2(root / name, destination / name)
    for name in ("beta-test-guide.md", "validation.md"):
        shutil.copy2(root / "docs" / name, destination / name)
    notices = destination / "dependency-licenses"
    notices.mkdir(exist_ok=True)
    # Preserve the dependency wheel license notices next to the dynamically
    # bundled libraries; no game assets or save fixtures enter the package.
    from importlib.metadata import distributions
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
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, notices / "Python-LICENSE.txt")
    if sys.platform == "win32":
        # Low-integrity build workspaces can propagate their labels to Qt.
        # Relabeling requires a normal-integrity shell, which a Python build
        # subprocess in a restricted workspace may not have. Document the
        # scoped shell step instead of disabling Chromium's sandbox.
        print('After a build in a Low-integrity workspace, run in PowerShell:')
        print(f"icacls '{destination}' /setintegritylevel '(OI)(CI)M' /T /Q")
    print(destination, flush=True)


if __name__ == "__main__":
    main()
