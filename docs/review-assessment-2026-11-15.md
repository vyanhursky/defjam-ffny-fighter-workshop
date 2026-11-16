# Independent assessment of the November 15 review

Scope: Parts A–C at `4e0ad6e`. Part E is deferred by the owner. Baseline on
Windows: 235 Python tests passed, 5 skipped. Source PRs and pushes are authorized;
merges and a new release are not part of this work. Companion runtime PRs must
be announced separately and assigned to milestone 1.2.0.

All 41 items in A–C were assessed and addressed in the PR series below, including
two adjusted implementation decisions (B6 and B7). “Confirmed” describes the
source finding; it does not claim native game acceptance.

| Item | Assessment and implementation decision |
| --- | --- |
| A1 | Confirmed literal mismatch. Read distribution metadata, fall back to the checkout's pyproject, and explicitly bundle metadata in frozen apps. |
| A2 | Confirmed stale UI labels, limits and feature descriptions. Rewrite current player guides; retain historical release/progress evidence. |
| A3 | Confirmed 1 MiB CLI versus 16 MiB project/desktop limit. Share the exact limit and test an invented HD PNG through the CLI. |
| A4 | Confirmed identity-only cache key with no retained source reference. Use a content key covering all four fighter fields, including stats/styles; a hash of appearance alone is insufficient. |
| A5 | Confirmed worker-thread counter mutation. Qt supports cross-thread signal emission; the actual requirement is GUI-thread completion and progress delivery, including encoding failures. |
| A6 | Confirmed repeated base64/PNG verification and repeated image-size reads. PNG verify checks integrity without fully decoding pixels. Cache validated metadata with bounded memory; never cache mutable project validation results. |
| A7 | Confirmed unconditional preview and wardrobe reload in renderState. Gate expensive appearance work with a content key, preserving explicit refresh and temporary try-on behavior. |
| A8 | Confirmed source-regex dependency. Prefer a bounded, validated manifest; absent manifests alone permit legacy fallback. Cache stamps must include the manifest. Reader PR precedes runtime producer PR. |
| A9 | Confirmed locks and import staging in the title tree. Centralize path-keyed locks in the Workshop workspace across saves, restores and imports. Sibling staging preserves same-volume rename. This cannot lock out the game; retain stale-source checks. |
| A10 | Confirmed no cache retention or cleanup UI. Prune only owned, validated cache directories; protect the active cache, and expose path/size and explicit clearing. |
| A11 | Confirmed unbounded preliminary chooser read. Share a bounded stream reader with import_pack, including duplicate-key rejection. |
| A12 | Confirmed unconstrained release build dependencies and incomplete resolved provenance. Pin and record the build environment; this is dependency reproducibility, not a claim of byte-identical archives. |
| A13 | Confirmed raw exceptions in bridge and preview states. Separate player message from diagnostic detail, preserve detailed logs, and use a Details disclosure. |
| A14 | Confirmed corrupt remembered state is silently discarded. Keep missing-file startup quiet, report corrupt files once, and preserve fail-open behavior. |
| A15 | Confirmed all requests count toward navigation refusal. Serialize navigation after background reads, but continue guarding visible writes and unsaved changes. |
| B1 | Confirmed large action chains and duplicated resets. Extract handlers and document dispatch tables while preserving return shapes and ordering. The retail chain is shorter than the review's 350-line estimate. |
| B2 | Confirmed native dialogs embedded in dispatch with no focused coverage. Extract explicit dialog specifications and preparation handlers; simple table entries alone cannot express every multi-step import. |
| B3 | Confirmed three bridge implementations, dropped retail actions, and mixed rendering concerns. Share transport and scene primitives, then extract pure wardrobe, face and artwork helpers with Node tests. |
| B4 | Confirmed CSS overrides, duplicated layout declarations and important rules. Format first; consolidate shared tokens/components separately from workflow changes. Exclude vendored assets from formatting. |
| B5 | Confirmed dense Python and no lint gate. Separate formatting from lint fixes; exclude attributed vendored decoders. |
| B6 | Confirmed untyped internal document boundaries. Added typed contracts, fully strict outfit operations, checked project functions and the snapshot builder with pinned mypy in CI. Whole-editor strict migration is deliberately incremental: untyped handlers and imported codec/catalog calls remain explicit exceptions. |
| B7 | Confirmed repeated payload, but measurement found embedded atlases/portrait dominated: 25,193,000 bytes. Remove those unused bytes from the summary (10,026 bytes after), retaining coherent catalogs in snapshots. A catalog-version protocol would add state/ordering complexity for little remaining payload benefit, so that specific proposal is declined. |
| B8 | Confirmed nested geometry arrays. Use explicitly little-endian typed buffers; retain 32-bit index support instead of assuming Uint16 is always safe. Measure payload and conversion cost. |
| B9 | Confirmed no Bridge pytest coverage and thin JS coverage. Add synthetic Qt/WebChannel coverage, deterministic native-dialog adapters and a scheduled asset-free tour. Original-asset smoke tests remain a separate local check. |
| C1 | Confirmed profile/backups aside remains in project mode. Show the active project and outfit controls; keep profile selection for starting a project. |
| C2 | Confirmed wrapping tab grid. Use four named groups (the suggested text says three but lists four), with an accessible vertical list. |
| C3 | Confirmed manual performance catalog connection from Voice. Connect on first relevant tab and show loading/failure placeholders. |
| C4 | Confirmed Pending Changes follows scrolling tab content. Pin a collapsible summary and Undo/Reset above save. |
| C5 | Confirmed export is buried and no preflight dialog exists. Add sticky export and a checklist using current runtime and draft state; compiler validation remains authoritative. |
| C6 | Confirmed ambiguous create-project control inside a project. Rename and relocate the new-identity action while preserving Save As identity. |
| C7 | Confirmed separate retail structure and narrow metadata IDs. Share shell components and improve metadata/start state while preserving all deployment modes. |
| C8 | Confirmed repeated donor selectors with insufficient explanation. Keep one start donor and disclose independent donor mixing with current values. |
| C9 | Partly confirmed: Textures already requests a preview when an appearance resource exists, so it is not wholly blocked by the refresh button. The blank viewer and missing post-import preview still need fixing. |
| C10 | Confirmed labels discard the build hash. Use installed metadata when available and retain a disambiguating build suffix consistently. |
| C11 | Confirmed stacked header/strip/wrapping tabs consume space. Fold paths into the compact header; verify usable first controls at both review sizes. |
| C12 | Confirmed small text, whole-control opacity and missing tab semantics. Raise minimum text sizes and add keyboard/ARIA tab behavior with responsive checks. |
| C13 | Confirmed outfit operations are split. Implement with C1; retain the viewer selector as a synchronized mirror. |
| C14 | Confirmed CAF UI donor is free text. Populate a stable-identity catalog selector and explain disconnected state without losing the saved choice. |
| C15 | Confirmed inconsistent version labels and hidden workspace path. Share a friendly version formatter across all three pages and expose workspace in Game setup. |
| C16 | Confirmed shortcuts lack discovery. Add tooltips and Messages help; verify existing keyboard handling. |
| C17 | Confirmed same-document fragment navigation without a hash handler. Reload only when changing fragments within the same document; test navigation and cancellation in Qt. |

Planned PR milestones: release hygiene; current docs; mechanical Python and
frontend formatting; dispatch/dialogs; GUI-thread/error/navigation fixes;
performance and transport; runtime capability reader then companion producer;
storage/cache/build environment; frontend modules and typed boundaries; shared
CSS; workflow improvements and synthetic UI coverage. A4, A15 and B6 are
explicitly included although missing from the review's suggested PR sequence.

## Completion evidence

### Review and merge order

These are stacked source PRs. Follow the order below, then update the next PR's
base as its parent lands. Nothing has been merged or released by this work.
The originally parallel capability and documentation PRs now sit on top of the
implementation stack so their diffs remain focused and the final head combines
every change.

| Order | PR | Review items / purpose |
| --- | --- | --- |
| 1 | [#12](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/12) | A1/A3/A11/C15: version, shared atlas limit, bounded manifest reads |
| 2 | [#15](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/15) | B5: mechanical Python format, lint gate |
| 3 | [#16](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/16) | B4 preparation: mechanical first-party UI format |
| 4 | [#17](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/17) | B1: dispatch handlers/tables and reset helpers |
| 5 | [#18](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/18) | A5/A13/A14/A15/C17/B9: GUI-thread completion, errors, navigation tests |
| 6 | [#19](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/19) | B2/B9: native dialog preparation and cancellation/bounds tests |
| 7 | [#20](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/20) | A4/A6/A7/B7: content cache keys, bounded PNG metadata, lean snapshots |
| 8 | [#21](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/21) | A9/A10: shared workspace locks, sibling import staging, safe cache retention/clear |
| 9 | [#22](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/22) | A12: pinned core build environment and complete resolved provenance |
| 10 | [#23](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/23) | B3/B8: shared frontend/viewers, modules and typed geometry transport |
| 11 | [#24](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/24) | B4/C12: consolidated CSS, readable type/focus/disabled states |
| 12 | [#25](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/25) | C1–C6/C11–C14/C16/B9: CAF workflow and scheduled synthetic Qt tour |
| 13 | [#26](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/26) | C7–C9 and retail C11/C12/C16: donors, layout, body/preview workflow |
| 14 | [#27](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/27) | B6: checked document contracts and explicit typing adoption scope |
| 15 | [#14](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/14) | A8/C10: manifest reader and distinct installed build labels |
| 16 | [#13](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/13) | A2: player guides synchronized with final source UI and this audit |

**Companion runtime change:**
[DefJamFFNY-recomp #267](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/267),
assigned to **v1.2.0**, publishes the capability manifest and verifies it against
the real CLI/recipe constants with AST drift tests. It leaves the existing CLI
literal readable by older Workshop versions. Workshop's absent-manifest fallback
also keeps earlier runtimes usable. This is the only runtime companion PR in
this review. No runtime merge, packaged release or game launch was performed.

### Integrated validation and limits

- Windows integrated source: **311 Python tests passed, 5 skipped**; **19 Node
  tests passed**; configured mypy adoption set, Ruff and Prettier pass. The static
  negative probe rejects wrong fighter/snapshot keys and incompatible argument
  types. The 5 Python skips are target-specific platform checks, not hidden failures.
- Real Windows synthetic Qt/WebChannel/WebGL tour passes **31 checks** at
  **1440×940 and 1100×760**. It covers all four Home workflows, unknown Story bytes,
  backup, project/outfit changes, failed/retried automatic catalogs, keyboard tabs,
  pinned changes, export readiness/save, retail donors and all deployment modes,
  and exactly one automatic preview after body import. Captures were inspected
  locally and stay untracked. Scheduled/PR Linux tours upload text receipts only.
- Original-resource/catalog/compiler boundaries and native picker answers are
  deterministic adapters. Synthetic editor coverage does not establish original
  asset decoding, real compiler output, native gameplay or manual macOS/Linux
  acceptance. Native package CI separately builds and relocates each of four targets.
- Runtime companion: **1,875 source unit tests passed, 778 skipped**, source
  hygiene has zero failures. The pinned toolkit submodule was initialized before
  the clean native run; earlier sandbox junction/submodule failures were resolved.
  The actual Workshop reader accepts this companion manifest with every declared
  feature enabled. Runtime CI is green; milestone assignment was verified.
- Invented HD project benchmark: repeated validation **118.59 ms → 0.33–0.36 ms**
  warm; state payload **25,193,000 → 10,026 bytes** after excluding unused embedded
  image data. B7's catalog-version protocol is declined because the measured
  remaining catalog payload is small and coherent snapshots avoid ordering state.
- Invented 12,000-vertex geometry: **2,090,522 → 544,373 bytes**; five-run median
  encoding **29.48 ms → 6.81 ms** including typed packing. No real-game performance
  claim is inferred from synthetic measurements.
- B6 intentionally adopts checking at document/project/outfit/snapshot boundaries;
  other editor handlers remain a documented migration, not claimed fully strict.
  A12 pins core dependencies and records the full resolved environment; it does
  not promise byte-identical archives or a fully locked transitive dependency graph.
- Part E remains deferred. Original saves/assets and unrelated worktrees remain
  untouched. No screenshots, extracted game content or generated binaries are
  added to Git; no PRs are merged and no release is published.

- Release hygiene (A1/A3/A11/C15): 239 Python tests passed, 5 skipped;
  8 Node tests passed. Includes an uninstalled-checkout version test, a real
  4 MiB invented PNG through CLI import, and oversized manifest refusal.
  Frozen startup remains gated by native package CI; no native game claim.
