# Native build environment

Native package CI runs Python 3.13 separately on Windows, Apple Silicon/Intel
macOS and Linux. `requirements-build.txt` pins the build backend, Qt,
PyInstaller, Pillow and NumPy. Install those first, then install the project
without build isolation and with the same constraints so editable-build setup
cannot silently select a different backend.

```sh
python -m pip install -r requirements-build.txt
python -m pip install --no-build-isolation -c requirements-build.txt -e '.[desktop,dev,build,ps2]'
python scripts/package_desktop.py
```

Each package contains `documentation/build-environment.json`, recording its
Python version, OS/CPU and every resolved distribution name/version, including
transitive dependencies. It includes no local paths. Release staging checks
the record's platform, bounds and required fields, and includes it for each
target in release `provenance.json` alongside source, hashes and startup checks.

`requirements-tested.txt` is a historical local snapshot. A developer's active
environment can differ from CI; the packaged record describes what actually
built that artifact. Core dependency pins and resolved provenance do not claim
byte-identical archives or a full per-OS transitive lockfile. Native startup and
gameplay qualifications remain separate.
