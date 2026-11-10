# defjam-ffny-fighter-workshop

- Owner approved voice overrides, original entrance/victory selection, source
  animation playback and AI personality authoring on 2026-11-10. Target exportable
  projects first and preserve Story-save workflows. Use versioned portable
  resources and the matching runtime; never store these fields in unknown save
  bytes. The owner deferred broad regressions until joint testing after more
  features. Focused codec, desktop and compiler checks remain appropriate.

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
  the released profile editor. On 2026-11-09 the owner authorized pushing both
  feature branches and PRs: Workshop into develop/0.1, runtime into
  research/custom-fighter-mods, with Windows/macOS/Linux CI passing. No new
  packaged release or merge is authorized by that instruction.

- Owner approved the texture-mod fighter pilot on 2026-11-09 and authorized
  general-purpose Workshop feature PRs against the existing roadmap. This covers
  experimental read-only PS2 snapshot recovery, portable CAF atlas import and
  preservation of retail finisher assignments, with an explicit companion
  runtime contract. Preserve beta profile workflows; keep source art, projects,
  captures and native evidence private. No new packaged release is implied.

- Owner approved editable four-slot Blazin' assignments on 2026-11-09 for Story
  CAFs and standalone CAF projects, using the complete original-game move pool.
  Keep selection provider/identity based so future custom animation resources
  can extend the menu; unsupported resource types remain refused until their
  format/runtime capability exists. Source PR updates remain authorized.

- Owner approved one custom fighter with up to three selectable outfits on
  2026-11-09. Extend standalone projects and the explicit runtime contract, with
  shared identity/combat settings and per-outfit appearance, atlases and portrait.
  Use the original clothing selector; preserve existing profile workflows and
  project versions. This targets roadmap fighter modpack authoring. Source PR
  updates are authorized; original assets remain private and releases need approval.

- Owner approved complete fighter UI art import on 2026-11-09, covering portraits,
  titlecards, result/grid icons and all 2/3/4-player variants. Shared defaults and
  outfit overrides belong to roadmap modpack authoring; preserve original-profile
  workflows. Use Pockets placeholders after the requested imagegen refusal.
  Source-only Workshop/runtime PR updates are authorized; no release or art publication.

- Owner approved facial authoring on 2026-11-09: original facial presets for
  Story CAFs and standalone fighters, experimental proportion controls and
  prioritized template mesh import research/implementation. Store sculpts in
  versioned projects and the companion runtime, never unknown Story save bytes.
  Preserve topology/UV/rig contracts and report native qualification limits.
  Source-only roadmap feature PRs remain authorized.

- Owner approved retail fighter movesets on 2026-11-10 for projects and direct
  Story-save editing, explicitly including companion runtime compatibility.
  Keep the CAF's appearance, career/training and four Blazin' assignments;
  select complete original motion cores by stable retail identity. Preserve
  the original CAF combination and old formats. Document native qualification
  separately from editor/codec tests; no release or merge is authorized.
