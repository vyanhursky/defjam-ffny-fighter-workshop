# Beta validation — 2026-11-07

The source repository contains invented fixtures and research notes. Actual
saves, game assets, screenshots, memory observations and per-run receipts remain
in a private sibling directory and are excluded from Git and packages.

## Codec and transactions

Thirty synthetic tests cover the signed container, profile identity/discovery,
bounded field edits, normal stat limits, style-combination and bonus updates,
unknown-byte preservation, original backups, stale-source rejection, full-profile
transfers, duplicate identity/collision handling, archive traversal rejection,
writer locking and vectorized texture decoding against an independent reference.

## Desktop

Fifteen checks use the real Qt page, WebChannel, controls, preview and persistence.
Only native file/name pickers and confirmation responses use deterministic
adapters. All writes use explicitly marked disposable data. Checks cover initial
preview, cash and health edits, undo, style combination, body build, retail tattoo
selection/equipping, export, duplication, editing/saving the duplicate with a
backup, final preview, switching destination and complete-profile import.

The earlier eleven-step run also passed with Qt 6.12 and pinned Qt 6.8.3.
The initial packaged renderer failure was traced to Low-integrity labels
inherited from the build workspace. Normalizing only the generated application
folder to ordinary Medium integrity fixes startup with Chromium sandboxing on.

## Native game acceptance

A codec-rewritten copy of a real profile reached the Story crib. A second copy
was edited, exported, imported and duplicated with a new ID. It loaded with cash
10,000,000, development points 100,000, training stats 30/35/40/25/45, and
Kickboxing + Martial Arts (combined ID 108). Body build F, changed skin, a blue
Ecko jacket and a tattoo were included alongside preserved accessories.

The game then saved through the normal Story crib Exit/Yes flow. Logs show the
retail MemCard.Save path opening the duplicated profile for overwrite. The
result remains correctly signed and a fresh process loaded it into the crib and
wardrobe. Exact current-profile memory records verified the edited fields;
wardrobe captures provide visible appearance evidence. No crash marker occurred.

The dedicated source fixtures and all four owner's fighter profiles retained
their original hashes. An unrelated concurrent game changed global Options;
it was not overwritten or restored. Early exploratory receipts with changing
fixtures are retained as failed evidence and are not counted as passing tests.
Concurrent runs were authorized for functional checks, so these are not
performance measurements.

## Remaining acceptance

Owner hands-on review, broader retail outfit comparisons and native macOS/Linux
package/game tests remain outstanding. Native checks verify representative
appearance/style changes and profile persistence, not every combination or move.
Development source publication on `develop/0.1` is authorized. No packaged release
has been authorized; source publication does not imply owner acceptance.
