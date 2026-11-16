# Independent assessment of the November 15 review

Scope: Parts A–C at `4e0ad6e`. Part E is deferred by the owner. Baseline on
Windows: 235 Python tests passed, 5 skipped. Source PRs and pushes are authorized;
merges and a new release are not part of this work. Companion runtime PRs must
be announced separately and assigned to milestone 1.2.0.

Each item below was checked against its implementation, rather than accepting
the proposed fix as a requirement. “Confirmed” describes the source finding;
it does not claim native game acceptance. PRs will update completion evidence.

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
| B6 | Confirmed untyped internal document boundaries. Add typed internal contracts and a checked adoption path; broad strict checking must account for the intentionally validated dynamic input boundary. |
| B7 | Confirmed stable catalogs repeated in snapshots. Separate versioned catalog data, invalidate on data/catalog changes, and retain script callers' documented behavior. |
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

- Release hygiene (A1/A3/A11/C15): 239 Python tests passed, 5 skipped;
  8 Node tests passed. Includes an uninstalled-checkout version test, a real
  4 MiB invented PNG through CLI import, and oversized manifest refusal.
  Frozen startup remains gated by native package CI; no native game claim.
