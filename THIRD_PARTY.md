# Third-party source

`src/defjam_caf/_vendor` includes the CAF-only decoder/assembly foundation from
[DefJam-Modding-Tools PR #5](https://github.com/vyanhursky/DefJam-Modding-Tools/pull/5),
MIT, copyright 2026 Vlad Yanhursky, snapshot
`9bb5b834b6c39e82f69ee93035a0803b1b62a8d3`. License included alongside the code.
The texture/model readers are trimmed to their decode APIs; the fighter catalogue
is replaced by a CAF-only adapter. No game-derived assets are included.

`src/defjam_caf/resources/vendor` contains Three.js r180 (0.180.0), MIT,
copyright Three.js authors. Upstream file hashes, URLs and license are included.
Only the core renderer and OrbitControls are used. No CDN or network access is
required at runtime.

The desktop application uses PySide6/Qt under its applicable LGPL/GPL/commercial
licenses. Packaged builds must include the dependency license notices and use
dynamic libraries. Pillow, NumPy, Python and PyInstaller retain their respective
licenses in the packaged dependency notices. No modified Qt build is shipped.

The app icons in `src/defjam_caf/resources/branding` are reused byte for byte
from DefJamFFNY-recomp at the owner's request (2026-11-07). See the accompanying
`provenance.json` for source paths, commit and SHA-256 fingerprints. They contain
the game's artwork, which remains the property of its rights holders and is
not covered by this project's MIT license.
