# Desktop platforms

Build each OS and CPU natively. These are standalone PyInstaller packages with
Python, Qt WebEngine, Pillow, NumPy and the offline UI included. They do not
contain saves or game assets. Packaging does not publish a release.

## Run from source

Use Python 3.11–3.13 (the pinned Qt 6.8.3 wheels do not support Python 3.14).
Create a virtual environment before installing:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[desktop,dev,build]'
defjam-caf-desktop --data /path/to/recomp-data
python -m pytest -q
python scripts/package_desktop.py
```

On Windows use `py -3.13 -m venv .venv` and `.venv\Scripts\Activate.ps1`.
`requirements-tested.txt` records the original Windows build; it is not a
cross-platform lockfile. The project extras select platform-native wheels.

## macOS

Build on macOS 12 or newer using a native Python 3.11–3.13. The package matches
the build interpreter's CPU: build Apple Silicon and Intel separately. An
Apple Silicon build is not an Intel/universal build. Dependencies may raise the
minimum macOS version: the local NumPy 2.5.4 wheel requires macOS 14; use
compatible dependency wheels if building for an older OS. No older OS is
qualified by a build on a newer host.

The output is `dist/defjam-ffny-fighter-workshop.app` and a versioned macOS ZIP
with a SHA-256 sidecar. Extract the ZIP, move the app to Applications if desired,
and open it. The beta uses ad-hoc signing; it is not Developer ID signed or
notarized. If Gatekeeper blocks a downloaded copy, use macOS System Settings →
Privacy & Security → Open Anyway for this app.

Documentation and dependency notices are inside
`Contents/Resources/documentation`. Do not modify the bundle after signing.

## Linux

Build on the oldest Linux distribution you intend to support; PyInstaller does
not bundle glibc. The Qt 6.8 wheels require glibc 2.28 or newer and a supported
CPU wheel. The CI workflow targets Ubuntu 22.04 x64; this does not qualify every
distribution, GPU or Wayland compositor.

Install a desktop session, OpenGL/EGL drivers, and Qt's X11/XCB libraries. For
Ubuntu 22.04/24.04 the runtime prerequisites are:

```sh
sudo apt-get install libegl1 libgl1 libnss3 libnspr4 libdbus-1-3 libfontconfig1 \
  libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \
  libxkbcommon-x11-0 libxkbcommon0 libasound2
```

Extract the versioned `linux-x64.tar.gz` and run
`./defjam-ffny-fighter-workshop/defjam-ffny-fighter-workshop`. Keep the complete
folder together. The tar archive preserves executable permissions and symlinks;
no installation or root access is needed. Use `QT_QPA_PLATFORM=xcb` to select X11
through XWayland if a Wayland setup has problems. Do not run the app as root or
disable the Chromium sandbox. Minimal/headless systems need a display server
and working GL support even though the UI is offline.

## Workspaces and diagnostics

On macOS, normal startup uses the Recomp installer's default
`~/Library/Application Support/DefJamRecompiled/data` when an FFNY title-save
directory exists there. The folder picker starts there too. An explicit
`--data` path takes priority. If no installation is found, the app opens normally
with manual selection. This discovery reads the directory without changing saves.

Choose the Recomp **data** directory containing `save` and `extracted` on other
platforms, or for a custom installation. All assets are read locally; Xbox asset names are resolved without
case sensitivity, including on case-sensitive Linux volumes. Ambiguous names
are rejected. Hex profile directory collisions are also rejected on Linux.

By default, the workspace uses Qt's AppLocalDataLocation:

| Platform | Workspace |
| --- | --- |
| Windows | `%LOCALAPPDATA%/FFNY Community Tools/defjam-ffny-fighter-workshop` |
| macOS | `~/Library/Application Support/FFNY Community Tools/defjam-ffny-fighter-workshop` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/FFNY Community Tools/defjam-ffny-fighter-workshop` |

Backups are in `backups`, the decoded cache in `assets`, and packaged diagnostics
in `logs/desktop.log`, all under that workspace. `--workspace /path/to/workspace`
overrides the whole workspace, including logs. The app never writes its cache
inside the installed application.

For a read-only packaged startup check (no game data required):

```sh
# macOS
./dist/defjam-ffny-fighter-workshop.app/Contents/MacOS/defjam-ffny-fighter-workshop \
  --workspace /tmp/workshop-check --smoke-test /tmp/workshop-startup.json
# Linux
./dist/defjam-ffny-fighter-workshop/defjam-ffny-fighter-workshop \
  --workspace /tmp/workshop-check --smoke-test /tmp/workshop-startup.json
```

Exit 0 requires the actual offline JavaScript modules, WebGL 2 and Qt WebChannel
to initialize. Renderer failure or a 120-second timeout exits 1. The receipt
records the platform, CPU, frozen status and whether the app icon loaded.
With no `--data`, automated smoke mode skips installer-data discovery so CI
never reads an existing user installation. This checks startup, not a fighter
preview or native game acceptance. Use `scripts/desktop_smoke.py` on marked
copies for the full 29-step editor check. Keep its captures and receipts private.

## App icon

The app reuses the owner's approved Def Jam Recomp icon: `.icns` for the Mac
bundle/Dock, `.ico` for the Windows executable and a PNG window icon on other
platforms. Source paths and exact fingerprints are recorded in
`src/defjam_caf/resources/branding/provenance.json`. The game artwork remains
outside the project MIT license. No icon is regenerated during packaging.
