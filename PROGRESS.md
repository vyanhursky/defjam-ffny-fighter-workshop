# Progress and handoff

## Status — 2026-11-07

Local beta implementation is present. Source publication is authorized on
`develop/0.1`; owner hands-on validation is still pending. No packaged release
has been authorized or published.

- Mapped and implemented cash/development, five training stats0–50, five retail
  styles and55 combinations with dependent bonus correction, and CAF appearance.
- Full-profile export/import and duplication, atomic save with original backup,
  stale-source checks, kernel writer locks and preservation of unknown bytes.
- Source asset cache and offline desktop Three.js UI; actual saved face morphs,
  scalp variants, hats/hair fits, clothing color/fitting, jewelry and tattoos.
- Thirty synthetic tests pass. Eleven real Qt/WebChannel controls/persistence
  checks pass with Qt6.12 and pinned Qt6.8.3 on marked disposable data. The
  extended fifteen-step run adds retail tattoo equipping and destination import.
- Native codec-rewritten VY3 reaches Story crib. Edited/exported/imported/duplicated
  CAFTEST loads, saves through normal crib Exit, and fresh-process reload reaches
  wardrobe. Resident current-profile records verify edited balances10m/100k,
  all five stats, Kickboxing+MartialArts combination, body/skin/clothing/tattoos.
  Retail MemCard.Save opens CAFTEST overwrite-if and leaves an exactly valid
  signed profile; fresh-process reload confirms the fields and appearance.
- Native save/exit and reload receipts have no crash markers and preserve source
  fixture identity. Owner's four fighter profiles are unchanged. Another game
  changed global Options; user approved concurrent functional checks only.
- Windows standalone package renders correctly with bundled Qt6.8.3. Renderer
  exit18 was caused by inherited Low-integrity file labels in the build workspace.
  Normalizing only the generated app folder to Medium resolves it with Chromium
  sandboxing enabled. Source-helper and isolated-runtime experiments are retained
  privately as diagnostic evidence; the delivered package uses PyInstaller.
- Packaged preview and actual stats-panel editing/undo were observed through
  Windows UI automation. User copies and an app shortcut are ready; the beta is
  left open with VY3 selected and no staged changes. Owner review is pending.

## Decisions and limits

Existing Recomp profiles only, full-profile transfer and Story-preserving
replication. New IDs conservatively use1–7 uppercase letters/digits. No fresh
Story-profile creation. All mapped retail items; XML-only right-wrist resources
have no proven valid retail-save encoding, so preserve rather than invent values.
Neutral static face preview preserves features; animation/expression/lighting
parity is deferred. Named fighter moveset overrides remain unverified.
Cash10m/development100k are conservative beta limits validated natively, not
claimed universal game maxima. macOS/Linux native builds and acceptance remain
outstanding. Game assets, saves and captures stay private and outside source.
Custom Fighter R&D, production art/review state and runtime source are untouched.

Early exploratory native tests failed guard checks because unrelated Options or a
private UI fixture changed concurrently. Keep those receipts as failed evidence;
later tests use dedicated immutable source fixtures and pass. Stop only exact
owned game PIDs. No performance claims from concurrent native runs.

## Evidence and next steps

Source-address evidence: docs/save-format.md and docs/research/*.md. Private
paths/commands belong in ignored .local-handoff.md, never public docs. Packaging
uses Python3.13.5, PySide6/Qt6.8.3, Pillow12.3, NumPy2.5.4, PyInstaller6.22.3.

1. Collect owner feedback using the copied-save launcher and beta test guide.
2. Address reported fit/appearance or editor issues and repeat affected checks.
3. Perform native Mac/Linux package/game acceptance before claiming those targets.
4. Publish development source on `develop/0.1`. Owner review remains a gate for a
   packaged release; publishing source does not imply owner acceptance.

Final verification: thirty tests pass using an explicitly writable temporary
directory. An initial repeat used an inaccessible sandbox temp directory and
failed during fixture setup; this is retained in logs and is not a product test
failure. Fifteen real desktop steps pass. Native current-profile samples and
resaved disk payloads match every expected edited field. All four original
fighter hashes and the prepared owner copies match their starting identities.

Windows packaging in a restricted workspace needs the documented normal-shell
`icacls` step: the Python build subprocess can lack the relabel privilege. Only
the generated application folder is relabeled; no system policy is changed.
