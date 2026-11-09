# defjam-ffny-fighter-workshop

Read PROGRESS.md and docs/specification.md first. This is a separate, local-first
desktop CAF/save editor for the Xbox-based Def Jam FFNY Recomp.

- Preserve the owner's saves. Investigations read original saves; native tests use
  a separate data root and copies. Never start or stop another chat's game/viewer.
- Track source and invented fixtures only. No game assets, saves, decoded models,
  captures, generated guest code, private paths, or release binaries in Git.
- Keep unknown save bytes intact. Validate signatures and sizes before interpreting
  data. Unverified fields and unsupported formats are read-only, never guessed.
- A successful codec test is not native game acceptance. Record tests and limits
  honestly in PROGRESS.md. Export, backup, import and duplication are distinct.
- Beta: existing Recomp profiles; full-profile export/import and duplication;
  all retail CAF items; normal stat caps; verified currency limits. Movesets must
  work through the profile alone. No companion runtime mod in beta.
- Reuse attributed MIT source from Modding Tools PR #5 for static CAF assembly.
  Keep this utility independent of its production corpus/review workspaces.
- Packaged Windows/macOS/Linux desktop application; offline assets and dependencies.
  Verify each target natively before claiming it is tested.
- Source publication is authorized on `develop/0.1`. Owner hands-on validation
  remains pending; do not publish a packaged release without a new instruction.
  Update PROGRESS.md when work or decisions change.

- Owner-approved artwork exception (2026-11-07): reuse the exact Recomp app icon
  files under `src/defjam_caf/resources/branding/` (`defjam.icns`, `defjam.ico`,
  `defjam.png`). Their source paths/commit and SHA-256 hashes are recorded in
  `provenance.json` there. This is an icon-only exception, not general permission
  to track game assets. The MIT license does not cover that artwork.

- Owner-approved README screenshot exception (2026-11-07): the four exact
  `docs/media/workshop-*.png` files listed in `docs/media/SHA256SUMS` were reviewed
  and approved for publication. Keep this set pinned; further captures need a
  new approval. Game artwork in these images is outside the MIT license.
- Owner authorized the first packaged prerelease `v0.1.0-beta.1` (2026-11-07).
  Publish only native workshop packages from the tagged source's green CI,
  with checksums and provenance. Never include original saves, extracted assets,
  caches or any compiled game executable. Future releases require instruction.

- Owner approved roadmap steps 1–3 on 2026-11-08: standalone fighter projects,
  CAF-to-Custom-Fighter-Mod export and package metadata/presentation, reusing
  research/custom-fighter-mods and testing on that branch. This supersedes the
  original beta-only ban on runtime integration/R&D for this feature. Preserve
  the released profile editor; no new release or source push is requested.
