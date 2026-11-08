# Beta validation — 2026-11-07

The source repository contains invented fixtures and research notes. Actual
saves, game assets, screenshots, memory observations and per-run receipts remain
in a private sibling directory and are excluded from Git and packages.

## Codec and transactions

Thirty-one synthetic tests cover the signed container, profile identity/discovery,
bounded field edits, normal stat limits, style-combination and bonus updates,
unknown-byte preservation, original backups, stale-source rejection, full-profile
transfers, duplicate identity/collision handling, archive traversal rejection,
writer locking and vectorized texture decoding against an independent reference.
Preview-overlay coverage verifies that try-on, hidden clothes and rejected
selections preserve staged bytes, history, the source profile and exported data.
Four Node tests cover pose immutability, exact source T-pose restoration,
symmetric arm lowering, stationary torso/lower body, normalized normals,
accessory attachment and distinct preview silhouettes.

## Desktop

Twenty-nine checks use the real Qt page, WebChannel, controls, preview and persistence.
Only native file/name pickers and confirmation responses use deterministic
adapters. All writes use explicitly marked disposable data. Checks cover initial
preview, cash and health edits, undo, style combination, body build, retail tattoo
selection/equipping, export, duplication, editing/saving the duplicate with a
backup, final preview, switching destination and complete-profile import.
The expanded checks also exercise tattoo grouping, automatic item/color/fit
try-on without staging, rapid selector changes, an export that excludes the
try-on, temporary clothing visibility, every lighting mode, pose changes,
restoring clothes and Equip committing the preview into Pending Changes.

The earlier eleven-step run also passed with Qt 6.12 and pinned Qt 6.8.3.
The original fifteen-step and first twenty-six-step feedback runs also passed.
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

Full owner acceptance, broader retail outfit comparisons, native macOS game
acceptance, and native Linux/Intel Mac package/game tests remain outstanding. Native checks verify representative
appearance/style changes and profile persistence, not every combination or move.
Development source publication on `develop/0.1` is authorized. No packaged release
has been authorized; source publication does not imply owner acceptance.

## Pose scope

Wardrobe-inspired and Relaxed use the original bind-joint pivots with analytical
arm deformation shared by clothing, skin and wrist/hand accessories. Their
rotations and blending weights are editor approximations. The retail shop clip
and full game skinning are not decoded. The source T-pose remains exact and
every pose is temporary. Native save acceptance above concerns profile fields;
the new viewer controls are validated through pure-data and desktop checks.

## macOS/Linux portability — 2026-11-07

The Apple Silicon macOS source desktop and standalone ad-hoc-signed `.app` pass
Qt WebChannel and WebGL 2 startup with Qt 6.8.3/Python 3.13. The package was
extracted from its checksum-verified ZIP to a path containing spaces and a
non-ASCII character; strict deep signature verification and frozen startup pass.
The local host runs macOS 26.5.2. This is not evidence for older macOS or Intel.

Thirty-five Python tests pass on the local case-insensitive Mac filesystem; two
additional case-collision tests skip because they require a case-sensitive
filesystem. Four Node pose tests pass. Added tests cover mixed-case Xbox asset
lookup, ambiguity refusal, lowercase canonical/legacy profile collisions and
Linux archive executable modes, symlinks and checksums. No Linux executable was
run locally; tar-format tests on macOS do not establish Linux runtime support.

The native CI matrix targets Windows x64, macOS arm64/x64 and Ubuntu 22.04 x64.
It builds packages and checks their actual offline UI after relocation. The
workflow is prepared locally; no remote run is claimed. No game data is used in
CI, and no tagged release is created. The Linux check uses Xvfb/software GL;
a physical GPU/Wayland and native game checks remain distinct acceptance gates.

An initial full Mac desktop check hit the original 60-second preview deadline
while the first-use cache was being decoded. Its failed receipt is retained
privately. The harness now allows 600 seconds for that initial conversion and
retains the 60-second limit for subsequent steps. Its exit path bypasses the
production busy/unsaved close guard so a failed check cannot wait at a modal.

The repeat also exposed a fixture assumption at Equip: the copied fighter
already wore that item/color, so only its fitting byte changed. The harness now
checks item and fitting together. That failed receipt is retained. The subsequent
Mac source desktop run passes all 29 checks in 34.96 seconds, including backup,
export, duplication, save and complete-profile import. Hashes of all 21 original
save files match before and after. Private receipts distinguish these source
editor checks from the standalone frozen startup check.

The final frozen Mac app also loaded the imported copied profile and rendered
its actual fighter (`preview_ready: true`, WebGL 2, `frozen: true`) in 1.69 seconds
with the previously built private cache. That timing is a warm-cache startup,
not a first-use conversion or native game performance measurement.

## Installer default and app icon — 2026-11-07

Thirty-eight Python tests pass (two case-sensitive filesystem skips). The added
cases cover the Mac installer's exact default path, absent installation, explicit
path precedence, read-only discovery and unchanged behavior on other platforms.
A native source startup without --data selects the installed default title-save
directory, and Qt loads the reused `.icns` window icon. That local installation
contains no supported fighter profiles; no fighter rendering pass is inferred
from this particular discovery check.

The rebuilt standalone Mac app also opens the installer data default without
--data (confirmed in its captured UI). Its CFBundleIconFile is defjam.icns and
matches the reused source byte for byte. Checksum-verified ZIP relocation,
strict deep signature verification and frozen WebGL/WebChannel startup pass,
including icon_loaded=true. No native Windows/Linux run is claimed here.
