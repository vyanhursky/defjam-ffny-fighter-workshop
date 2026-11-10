# Progress and handoff

## Persistent imported artwork — 2026-11-10

Owner reported imported 2Pac tattoos reverting to original game artwork after
appearance changes. The preview had fallen back to retail RGB on a hash
mismatch, and project save required clearing/reimporting art. Imported PNG RGB
now stays applied across body, face, wardrobe/tattoo and temporary preview
changes. Project staging rebinds identical PNG bytes to the current outfit;
Clear/replace remains explicit. Original native material alpha is retained.
Undo, outfit switching, save/copy/reopen and export preserve per-outfit art.

153 Python tests pass, 3 skipped at the first checkpoint. With supplied 2Pac
art and actual source models, bodies A–F (normal and No clothes) plus face,
eyes, brows, nose, lips and ears preserved exact imported RGB; save/reopen and
complete runtime export passed. Evidence: logs/persistent-real-art.txt. Different
body UVs can affect fit; no repainting or automatic geometry/UV transfer.

## Immediate face slider preview — 2026-11-10

Owner requested instant geometry feedback while dragging, with Apply reserved
for staging. Unit-control deltas from the existing export generator now blend
directly into the WebGL head each frame; no per-drag backend/texture rebuild.
Preview stays separate from project data/history. Revert restores staged values;
Apply stages, Save persists. Pose and scene refresh retain the preview, while
fighter/outfit/state changes clear it. Imported-sculpt locking is explained
beside the sliders. Pending previews cannot be captured/exported as head art.

147 Python tests and 7 Node tests pass, including Python/JS deformation parity.
Actual Qt input events updated rendered vertices on the next frame (16.7 ms
observed), without staging or writing the project. Rapid inputs, Revert, Apply
parity, Undo, pose/scene refresh and Save passed in an isolated project.
Private evidence: logs/live-face-desktop.txt and live-face test workspace.
No runtime/geometry export contract change; native pilot evidence remains valid.

## Facial authoring — 2026-11-09

Isolated `feature/face-authoring` work extends the custom meshes/modpack roadmap
on the CAF texture/UI feature base. Basic controls expose face type, eye
shape/color, eyebrow shape/color, nose, lips and ears from verified original
resources. Unknown choices/bytes remain preserved. Story saves use native fields.

Experimental Advanced controls provide nine absolute proportion sliders. Expert
exports/imports a 710-vertex position-only OBJ template, preserving topology,
UVs, original rig and neck seam. Project v5 stores per-outfit sculpts with
Undo/Reset/save/copy support. CAF v4 exports hash-bound coordinates through the
companion `feature/caf-face-geometry` runtime. The runtime compares all reference
vertices before applying its original morph evaluator and verifies target
coordinates plus unchanged peer buffers. See [Face authoring](docs/face-authoring.md).

Integrated checks: 146 Python tests passed, 3 skipped; 4 pose tests passed.
Actual Qt preset/slider/history/save/reopen checks passed; original OBJ round-trip
error below 5e-8. Windows native two-CAF menu/combat pilot verified identities,
710 imported vertices within 1.5377998e-05 native units, unchanged peer buffers,
77 presentation intervals and no crash/watchdog/unresolved call. Isolated saves
restored identically. Complete mod export passed the runtime API. The first
overlong test display name correctly failed the existing native title budget.

Limits: original normals/rig and accessories retained; no arbitrary topology,
automatic rig/UV transfer or accessory refitting. Broader facial animation,
outfit/rematch, external DCC and cross-platform gameplay qualification remains
pending. Keep Advanced/Expert experimental. Original Tupac packages/playtest
roots are unchanged; all generated geometry, projects and captures stay private.
No merge or packaged release is authorized. Follow-up: owner review and the
broader qualification matrix before promoting sculpting beyond the pilot.

## Complete fighter UI artwork — 2026-11-09

Owner approved roadmap modpack authoring for selector/loading portraits,
titlecards, result icons and grid states. Audited Method Man/Blaze costumes and
Pockets against original movies: 24 distinct roles across 2/3/4-player layouts.
The UI artwork tab provides six master imports plus all advanced slots, independent
UI donor, retail-reference import, native/2×/4× output and effective-art preview.
Version4 embeds exact PNGs with shared defaults and sparse outfit overrides.
Undo/Reset/review/save/copy/variant/export preserve the complete collection;
old project formats and profile workflows retain their contracts.

The companion typed PNG compiler preserves original geometry/actions/material
controls, compiles all layouts, and stages verified HD replacement tiles after
selected texture packs for this launch without changing persisted settings.
Missing art uses the UI donor; retail grid placeholders derive from result icons.
Source and output budgets, hash checks and conflicts fail before ZIP publication.

Validation:124 Python tests pass (3 platform skips), plus4 Node tests. A real
Windows Qt/WebChannel workflow passes23 steps through full native export and
save/reopen. All24 roles compile for all3 outfits. Managed native launch passes
with the HD layer and3 CAF recipes/extras:16 present samples, median120/min108
per2s; zero crashes/watchdogs/unresolved calls; identical guarded saves.
Selector/loading/result native acceptance and current-head CI are recorded in
the source PR handoff. Windows evidence does not claim macOS/Linux gameplay.

The requested Tupac UI imagegen attempt was rejected at input; no image was
generated. Per owner instruction the private pilot uses Pockets placeholders,
with the original3 Tupac outfit textures. HD output is deterministic resampling,
not restored source detail. Private logs/ui-art-ui-proof1 and UI preview receipts
retain evidence; no art, captures, saves or binaries enter Git. Source PR updates
only; no merge or packaged release.

## Three-outfit custom fighter implementation — 2026-11-09

Owner requested one custom fighter with three outfits, following retail Blaze
and D-Mob. Work is in progress on the isolated Workshop/runtime feature branches.
The source archive supplies shirtless, red jersey and black tank art. Original
single-outfit project/pack and original saves remain read-only inputs.

Plan: version3 projects keep one shared fighter identity/combat configuration,
a default appearance and up to two additional named outfits with stable IDs,
independent appearance/atlases/portrait. Existing v1/v2 stay readable. Outfit
switching preserves all staged changes; Undo/Reset/save/copy/variant/export cover
the whole collection. Native menus retain one roster cell and use the original
three-choice clothing UI. A typed runtime-owned selector command carries the
chosen ordinal per participant; stock selectors/semantic fighter IDs stay intact.
No extra public fighter identities or raw package bytecode are introduced.

Implemented: collection schema/validation, staged editor/history/preview, Project
controls and complete CAF v3 export with per-outfit typed portrait references.
111 Python tests pass (3 platform skips), plus4 Node pose tests. Twenty real
Windows Qt/WebChannel steps pass: switching, rename, copy/remove, Undo/Reset,
three actual WebGL portrait captures and save/reopen of the complete collection.
The resulting three-outfit pack passes the actual runtime compiler/inventory.
The native selector displays three choices and the correct black-tank portrait;
index2 builds bodyA/face4/core101 under the original canonical100 identity, with
zero crashes/watchdogs/unresolved calls and identical guarded-save restoration.

The original CCharacter constructor reads additional CLOTH datasets from the
retail roster stream; the owned runtime initializes one normal dataset and fills
additional canonical datasets locally. Its visual-only aliases and bounded outfit
commands do not create ledger/progress identities. Native red-jersey gameplay/result acceptance passes seven combat checks and two
Options-save generations with identical guarded restoration. Detailed gameplay,
results, rematch/cancellation and final CI evidence are maintained in the companion PR
acceptance work. Native Windows evidence does not claim macOS/Linux gameplay.
Four native package CI jobs pass at9f7cd7c: Windows x64, macOS arm64/x64 and
Linux x64 (run42732816506). No merge or packaged release is included.
Private logs/outfits holds source/art
provenance, plan, desktop receipt and export validation; no assets are tracked.

## Editable Blazin' assignments — 2026-11-09

Owner approved a four-slot menu for Story CAFs and standalone CAF projects,
using the complete original-game move pool, with room for future custom moves.
Implemented a named catalog from the verified SODB DisplayName/choice schema;
all82 retail choices are available independent of styles/unlocks. Provider-qualified
stable keys and source-grouped options decouple the menu from native ordinals.
Custom animation providers remain a future versioned resource/runtime extension.

Four selectors stage an explicit complete selection; duplicates are allowed.
Profile writes affect only16 payload bytes at0x120, using normal backup/stale-file
checks. Projects retain retail record identities and may remove their override
with Use inherited moves. Undo/Reset, close/discard protection, named change
review, project conversion/copy/variant/export and existing texture bindings are
preserved. Unknown/unassigned values remain untouched until explicitly replaced;
missing original assets disable selection. No editor animation playback is claimed.

Validation:98 Python tests pass (3 platform skips), plus4 Node pose tests.
Seventeen real Qt/WebChannel steps pass on marked disposable data: draft versus
Apply, all four menus, duplicate choices, Undo/Reset, profile save/reload,
CAF-to-project conversion, inheritance, textured project edit/copy/reopen.
Decoded saved profile comparison confirms no bytes outside the four references
changed. The UI-edited textured project passes the actual CAF v2 compiler/export.
Native acceptance and updated cross-platform CI are in progress. Original saves,
projects, artwork and captures remain private; the existing2Pac delivery keeps
its original assignments. No merge or release is included.

## Texture-mod fighter pilot — 2026-11-09

Owner approved general-purpose roadmap work for native texture import and fighter
modpack authoring. This source branch builds on merged Workshop PR2. Existing
version 1 projects and full-profile workflows remain available; no release or
merge is included in this change.

Implemented project version 2: exact embedded 256×256 PNG atlases, appearance
binding, RGB-only preview, staged import/clear/reset, saved retail finisher
identities, and hash-bound CAF v2 export through the companion runtime compiler.
Source-profile conversion now preserves all four verified finisher assignments
instead of dropping them. Partial/unknown assignments are refused. The existing
Project tab provides native atlas controls; D1/D2 injury variants are retained
and exported but are not simulated in the current static preview.

Added experimental read-only PCSX2 snapshot inspection/recovery. The observed
layout is validated; SODB identities translate equipped items and finishers to
the player's Xbox dump. Archive/output/window bounds, CRC, conflicting-copy and
ambiguous-database refusal apply. No console Story-save conversion is implied.

Validation: 86 Python tests pass, 3 platform skips; four Node pose tests pass.
Nine real Qt/WebChannel atlas/portrait/persistence checks pass on marked disposable
Windows data. The private pilot recovers body A/0, Kickboxing → Streetfighting →
Wrestling (combined101), five training stats50, 16 matching equipped items and
four finishers (native choices52,38,30,39). It exports and compiles through the
companion CAF v2 runtime based on Recomp PR213 head81ce1d7.

Native Windows selection/portrait and one complete match versus retail Crack
pass seven combat/result assertions, two acknowledged Options-save generations,
and byte-identical restoration of the copied save root. Five imported RGB
atlases apply to the context-owned native visual. Captured torso/jeans/normal-face
RGB matches source PNGs exactly; native alpha is retained. An initial conversion
failure and incorrect Morton layout were detected, retained as failed evidence,
and fixed before the passing run. Four finisher assignments are verified at
native setup; playing every Blazin' cinematic is not claimed.

HD image restoration remains pending at the owner's request after imagegen
refused the face edit. Supplied textures are unchanged. Higher resolution,
arbitrary meshes, granular moves and animation playback remain deferred.
Exact assets, hashes, native logs and captures remain private. Cross-platform
packaging CI and broader owner/game acceptance are separate gates.

## Status â€” 2026-11-07

Local beta source is published at
https://github.com/vyanhursky/defjam-ffny-fighter-workshop on `develop/0.1`, the
default branch. The four owner-approved README screenshots are published.
The first packaged prerelease, v0.1.0-beta.1, is published with Windows x64,
macOS arm64/x64 and Linux x64 binaries, checksums and source/CI provenance. Broader owner/game acceptance remains ongoing. Saves and
original extracted assets stay private; binaries are release attachments only.

The chosen project name is Def Jam FFNY Fighter Workshop. Repository metadata,
desktop branding and future package filenames use `defjam-ffny-fighter-workshop`.

Preview feedback update: automatic item/color/fit try-on is isolated from Pending
Changes until Equip. Temporary No clothes hides apparel/accessories while
retaining underwear and tattoos. Tattoo categories are grouped and explicitly
prefixed. Three pose options and four lighting presets are available; the two
non-T poses use original joint pivots with approximate editor deformation, not
the retail shop animation. Full owner acceptance remains pending.

Feedback validation: 31 Python tests, four Node pose checks and 29 real desktop
steps pass on disposable copies. Checks include rapid selection changes,
uncommitted try-on exclusion from export, every lighting mode, all three poses,
temporary clothing visibility, explicit Equip, backups and full-profile import.
The Windows package has been rebuilt and its new default pose/controls rendered
successfully on copied profile data. The local test shortcut targets this build.

- Mapped and implemented cash/development, five training stats0â€“50, five retail
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
- Initial packaged preview and actual stats-panel editing/undo were observed
  through Windows UI automation. The owner-test handoff uses copied profiles
  and a local shortcut. Full owner acceptance remains pending.

## Decisions and limits

Existing Recomp profiles only, full-profile transfer and Story-preserving
replication. New IDs conservatively use1â€“7 uppercase letters/digits. No fresh
Story-profile creation. All mapped retail items; XML-only right-wrist resources
have no proven valid retail-save encoding, so preserve rather than invent values.
Neutral static face preview preserves features; animation/expression/lighting
parity is deferred. Named fighter moveset overrides remain unverified.
Cash10m/development100k are conservative beta limits validated natively, not
claimed universal game maxima. Apple Silicon macOS standalone package startup
and all 29 source editor checks are verified. Native package build/startup
checks now pass for Windows x64, Mac arm64/x64 and Linux x64; broader native
macOS/Linux editor/game acceptance remains outstanding. Game assets, saves and captures stay private and outside source.
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
4. Maintain development source on `develop/0.1`. Owner review remains a gate for
   a packaged release; publishing source does not imply owner acceptance.

Initial beta verification: thirty tests pass using an explicitly writable temporary
directory. An initial repeat used an inaccessible sandbox temp directory and
failed during fixture setup; this is retained in logs and is not a product test
failure. Fifteen real desktop steps pass. Native current-profile samples and
resaved disk payloads match every expected edited field. All four original
fighter hashes and the prepared owner copies match their starting identities.

Windows packaging in a restricted workspace needs the documented normal-shell
`icacls` step: the Python build subprocess can lack the relabel privilege. Only
the generated application folder is relabeled; no system policy is changed.

## macOS/Linux compatibility â€” 2026-11-07

Work is on `codex/macos-linux`, based on beta commit `84b3171`. No source push or
packaged release has been performed by this porting session.

- Resolve workspace and packaged logs through the same Qt native application
  data path; `--workspace` overrides cache, backups and logs together.
- Resolve Xbox asset names case-insensitively without changing the dump; reject
  ambiguous paths. Prevent lowercase hex identity collisions during discovery,
  import and duplication on case-sensitive filesystems.
- Package a correctly identified macOS `.app` with notices included before
  signing; create a symlink-preserving ZIP, Windows ZIP, or Linux tar.gz and
  SHA-256 sidecar. Build caches are scoped to this project's `build` directory.
- Add a frozen startup check for the offline modules, WebChannel and WebGL 2,
  plus a checksum/relocation/signature checker. CI defines native Windows x64,
  Mac arm64/x64 and Ubuntu 22.04 x64 builds; it has not been run remotely.
- Local evidence: 35 Python tests passed, two case-sensitive filesystem cases
  skipped, four Node pose tests passed. Mac source and frozen relocated startup
  passed on macOS 26.5.2 arm64 with Qt 6.8.3/Python 3.13. All 29 real source
  editor checks pass in 34.96 seconds, including save/backup/export/import and
  duplication. All 21 original save files retain their hashes. The final frozen
  app also renders the imported CAFTEST fighter (`preview_ready: true`) in
  1.69 seconds using the existing private cache. No Linux or Intel Mac
  native runtime pass is claimed; no native game acceptance was repeated.
- The initial full desktop check timed out during first-use decoding under its
  original 60-second deadline. Its failed receipt remains private. Give initial
  decoding 600 seconds, subsequent actions 60, and exit the test event loop
  without invoking production busy/unsaved close guards. A second failed receipt
  exposed an Equip assertion that assumed the item value changed, although the
  selected fitting alone changed; check both item and fitting bytes.

Next: run the prepared native CI matrix when source publication is requested,
then qualify representative packaged workflows on Linux/Intel and test edited
profiles in the game. Maintain the owner acceptance/release gate. Public docs
contain no private data paths; local receipts and copied saves stay outside Git.

## Installer data default and Recomp icon â€” 2026-11-07

Owner requested macOS discovery of the installer's default data directory and
reuse of the Def Jam Recomp app icon. Normal Mac startup reads
`~/Library/Application Support/DefJamRecompiled/data` when it contains FFNY title
saves; the folder picker defaults there. Explicit `--data` takes priority. No
matching installation leaves manual selection available. Workspace/cache/backup
locations stay separate from the game data. Automated smoke mode without --data
skips personal installation discovery.

The exact Recomp `.icns`, `.ico` and 256px PNG are reused, with SHA-256/source
provenance and the icon-only owner exception recorded in AGENTS.md/THIRD_PARTY.md.
The Mac bundle and Windows executable receive native icons, and Qt sets the app
and window icon. These game artwork files are not MIT-licensed.

Validation: 38 Python tests passed; two filesystem cases remain skipped on the
case-insensitive Mac. The native source app starts without --data at the real
installer default and loads its icon (the local default contains zero supported
fighter profiles). No profile write was performed by this discovery check.

The rebuilt standalone Mac app also opens the installer data default without
--data (confirmed in its captured UI). Its CFBundleIconFile is defjam.icns and
matches the reused source byte for byte. Checksum-verified ZIP relocation,
strict deep signature verification and frozen WebGL/WebChannel startup pass,
including icon_loaded=true. No native Windows/Linux run is claimed here.

## Native CI publication â€” 2026-11-07

Owner authorized source push and native Windows/macOS/Linux CI. The source is
pushed on `codex/macos-linux`, PR #1 into `develop/0.1`. No release is tagged.
Initial run: https://github.com/vyanhursky/defjam-ffny-fighter-workshop/actions/runs/42444607060

Linux x64 built and its relocated frozen WebGL 2/WebChannel/icon startup passed.
Windows and Apple Silicon Mac built, but startup timed out because Chromium
blocklisted the hosted VMs' software adapters (Microsoft Basic Render Driver
and Apple Software Renderer). Their failed receipts remain in CI artifacts;
do not treat these initial jobs as passes. Allow the virtual software adapters
with --ignore-gpu-blocklist only in the offline CI smoke steps, retaining the
actual WebGL 2 requirement and browser sandbox. Record the renderer in receipts.
The native application keeps its ordinary graphics defaults.

## Native CI results and handoff â€” 2026-11-07

Source is pushed in PR #1 on `codex/macos-linux` into `develop/0.1`:
https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/1
The corrected run built and started Windows x64, macOS arm64/x64 and Linux x64:
https://github.com/vyanhursky/defjam-ffny-fighter-workshop/actions/runs/42445039193
All four startup receipts report passed=true, frozen=true, icon_loaded=true,
WebGL 2 and working WebChannel after archive extraction/relocation. Mac signatures
verify strictly. Source documentation is updated to reflect native package CI.

The initial failures were Chromium's blocklist of the VMs' software adapters,
not a build/signature failure. Allow those adapters only in CI, keep requiring
WebGL 2, and keep the browser sandbox. Actual renderers are recorded in receipts.
Linux uses Mesa llvmpipe under Xvfb; Windows uses the Microsoft Basic Render
Driver, and both Macs use Apple Software Renderer. The application retains its
normal graphics defaults. Initial failed receipts remain in the earlier run.

Linux executes all 40 Python cases; Windows passes 37 with three skips, Mac
arm64 passes 38 with two skips. Four Node pose checks pass. The separate local
29-step editor/save/import test and unchanged-original-save hashes remain the
functional evidence for Apple Silicon. CI startup uses no save/game fixtures.

Next: use the PR's current-head check links and native package artifacts for
review. No tagged release was created. Full owner acceptance, physical GPU and
Wayland checks, and broader native game qualification remain distinct gates.

## PR #1 merged â€” 2026-11-07

Owner approved and PR #1 merged into `develop/0.1` at `5bbcccc`. The final PR
head `3878375` passed all four native CI jobs in run 42445695324: Windows x64,
macOS arm64/x64 and Linux x64. The merge preserves the tested source tree.
The default branch now runs native package CI on pushes as well as PRs.

The local checkout returns to `develop/0.1`; the merged feature branch is
removed after synchronization. No tagged release was created. Next work remains
owner acceptance and the broader native editor/game checks documented above;
CI package/startup evidence does not replace those checks.

## README screenshot approval â€” 2026-11-07

Owner requested four examples for the develop/0.1 README, with candidate review
before publishing: main window, stats/cash, fighting-style combinations and
clothing. Four actual Qt window captures were prepared from source 418d08d,
using a disposable DEMO profile and a generic temporary data path. Each capture
is 2880 x 2076; no pixel alterations or UI text replacements were applied.
The original source profile's hashes are unchanged.

The owner approved all four exact candidates. They are committed under
docs/media with SHA-256 pins and an artwork exception in AGENTS.md; the main
README shows the approved gallery. No original assets or saves are committed.

## 0.1 Beta 1 release authorization and handoff â€” 2026-11-07

Owner requested `v0.1.0-beta.1` with native binaries. Python package version is
already 0.1.0b1; the human-readable tag is v0.1.0-beta.1. The release is a GitHub
prerelease, never a stable/latest release. Native packages include linked README
documentation and the exact approved images; no original save/dump/cache or
compiled game code enters a package. The editor itself may be distributed.

Build all four targets on this source, retain their frozen startup receipts,
verify native archives and SHA-256 sidecars, then attach those exact CI outputs
with SHA256SUMS and source/CI provenance. Verify uploaded asset digests before
publishing. Notes: docs/releases/v0.1.0-beta.1.md. Release page:
https://github.com/vyanhursky/defjam-ffny-fighter-workshop/releases/tag/v0.1.0-beta.1

Next after publication: collect beta feedback using copied saves; keep broader
native game acceptance, physical GPU and Wayland qualifications distinct from
the native package/startup evidence. No fresh save creation or named-fighter
moveset override is claimed.

## Beta draft staging â€” 2026-11-07

The approved gallery/release source is a7a7e354df78b5eab6ecabbcf0c03430d129e910;
its native build run 42447467964 passed all four targets. Slow local artifact
transfers are replaced by a GitHub-hosted draft-staging workflow. It downloads
the exact green run's outputs, checks commit/tag/version binding, archive
integrity and native entry points, approved screenshot hashes and notices,
and rejects save/dump/compiled-game files. It attaches four native packages,
four sidecars, SHA256SUMS and source/CI/startup provenance to a draft only.
Uploaded GitHub SHA-256 digests are compared before any publication.

Publisher infrastructure is a later develop/0.1 commit; the beta tag stays on
the exact already-qualified a7a7e35 application source. Local staging fixtures
pass 44 Python tests with two filesystem skips (the tagged application suite
remains 40 cases). The owner authorized the beta publication; the final
publication step follows successful draft verification, without another prompt.


Initial draft staging run 42448226560 verified all four archives and uploaded
the ten assets, then failed because GitHub's by-tag REST endpoint excludes
unpublished drafts. The draft stayed unpublished. Resolve its numeric ID from
the authenticated release list, allow retries only for an unpublished draft
of the same source SHA, and verify all uploaded digests before publication.

## 0.1 Beta 1 published â€” 2026-11-07

Published https://github.com/vyanhursky/defjam-ffny-fighter-workshop/releases/tag/v0.1.0-beta.1
as a prerelease, not Latest. Tag/application source: a7a7e354df78b5eab6ecabbcf0c03430d129e910.
Native release build/startup CI 42447467964 passed all four targets. Corrected
server-side staging/verification run 42448445592 passed the archive/content
checks and all ten GitHub-uploaded SHA-256 comparisons. Release ID: 438038559.

Assets: four native archives, four .sha256 sidecars, SHA256SUMS and provenance.json.
The public checksum file was downloaded and compared byte for byte, and all
four README binary links match the published asset URLs. The approved gallery
is committed and pinned. Publisher infrastructure through 542ad01 also passed
all four native CI jobs in 42448445705. The tagged application suite and later
publisher-fixture tests remain distinct evidence.

The first staging run's draft lookup failure remains recorded above; its audits
and uploads had passed, and publication waited for corrected digest verification.
Next: beta feedback using copied saves, then broader editor/game/GPU/Wayland
qualification. No original saves, raw game assets or compiled game executable
were published; the exact approved screenshots/icon retain their artwork exception.

## Standalone projects and CAF mod export â€” development preview, 2026-11-08

Owner approved roadmap steps1â€“3 with public Custom Fighter R&D and in-game
acceptance. Local branch codex/fighter-projects starts from develop/0.1 at834c2bb;
the released Beta1 is unchanged. No push or new release was requested.

Implemented: versioned fighter-only .ffnyfighter projects with appearance,
five training stats and retail styles; open/edit/save/Save As independent of
the source profile; stale-save/collision protection; no career/currency/profile
bytes. Creating a variant preserves credits/portrait and generates a fresh pack
identity; Save As preserves identity. Metadata and PNG portrait drafts participate
in discard/close protection. Qt adds Project & mod controls, current-view capture/
import and validated ZIP export through the compatible runtime's shared authoring/
native menu compiler. Frozen apps use bundled Python in a child process for the
explicitly selected development checkout. Exports never run code from a mod pack,
write a Story save, auto-install or publish the pack.

Runtime companion codex/workshop-caf-export starts from public
research/custom-fighter-mods at807fd41, toolkit4801dc1. It adds caf-fighter-1,
native CAF assembly/participant contexts, combat stats, original retail style
combinations, explicit retail voice-template inheritance and native portrait
retiling. Existing registry/package/menu/profile-store contracts are reused.
No game executable, original assets/saves/generated code/captures enter source.
Stable Beta1 does not provide this extension. Workflow: docs/fighter-projects.md.

Workshop checks: **61 Python tests passed, two filesystem skips**. Real macOS Qt
workflow passed12 steps covering project editing/reopen, metadata, portrait
capture/save, unsaved details/reset and complete ZIP export. Final frozen Mac
build starts in1.01s with two copied profiles, WebChannel/WebGL preview and icon.
Its bundled helper validates a complete portrait-bearing pack against the updated
compiler. Earlier bundled PNG conversion also passes. Node is unavailable on
PATH; pose source is unchanged. Windows/Linux in-game acceptance is pending; hosted package/startup results follow below.

Runtime native build passes143 manual-address checks. Fighter fixtures initially
passed1437; after adding CAF teardown cleanup, an aggregate had1432 passes/five
fixture compile errors. The updated existing fixture verifies cleanup after
resource destruction and all five cases pass. CAF/portrait/authoring API checks
pass14. Final stock quick regression passes **5/5** in seven minutes:
logs/regress-20261108-230945.txt. It includes2367 unit passes,74 skips and one
slow-test deselection; three matching golden frames; and120 seconds of stock
combat at median120/min113 presents per two seconds. The final aggregate also
accepts the updated teardown fixture.

**Native two-CAF acceptance passes** on Apple Silicon:
run-20261108-225834.log.err, caf-dual-audio-probe.txt. Both exported recipes
construct/assemble, exact menu identities100/101 and cores94/109 are verified,
and all **7 combat/result checks** pass. Both fighters move/attack/take damage;
a decisive result reaches the native summaries, Options writes/closes5404bytes,
and one profile-store generation commits. The route returns to Battle.96
2-second frame samples: min77/median120/max121; zero native fault signatures.
The complete disposable save root restores identically. An independent audit
also matches all21 original save-file hashes. This is a two-participant slice,
not qualification of every combination/venue/platform.

Retained failures: debug cp_def XML overwrote an assembled CAF and crashed;
body-only initialization stalled motion at step31; the preview-only1.5MiB arena
corrupted the second CAF's palette; the native Battle lookup required a Story
profile for the CPU; native CAF audio rows caused an SCEl stream-chunk loop.
The fixes retain full native initialization, normal match allocators, direct
live participant/context binding and declared retail speech templates. Earlier
input-selection mistakes also remain failed commands; separate actual-pair
checks accept a prior CAF-versus-retail combat/result/save run. Exact evidence,
ABIs and failed runs are in the runtime companion's R&D report.

Limitations: original retail style combinations only; unsupported appearance
encodings refuse export. CAF generation currently combines with sourced portraits
but refuses other sourced fighter components. PNG portraits/metadata are included;
individual move/model/texture authoring and animation playback are later work.
Export compilation does not claim game acceptance or activate a mod. Existing
Custom Fighter runtime shipping/installation/profile/capacity gates still apply.

Ready for review as source-only local feature branches in persistent repositories. Before a new release, qualify
Windows/Linux gameplay and the matching runtime/launcher integration. No source push or
release publication this turn.

## PR publication and cross-platform CI â€” 2026-11-09

Owner authorized publishing codex/fighter-projects into develop/0.1 and the
companion recomp codex/workshop-caf-export into research/custom-fighter-mods.
Open both PRs, preserve the native evidence above, and complete Windows, macOS
and Linux CI. No merge or new release is requested. This supersedes the earlier
no-push handoff for this feature. Workshop PR: https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/2.
Companion runtime PR: https://github.com/vyanhursky/DefJamFFNY-recomp/pull/213.

Workshop CI run42640408538 passes all four native package targets at8a8e0ab:
Windows x64, macOS arm64, macOS x64 and Linux x64. Each runs Python/pose tests,
builds the game-free package, relocates it through a path with spaces/non-ASCII,
and verifies frozen WebChannel/WebGL/icon startup plus the synthetic authoring
subprocess and DXT5 portrait encoder.
https://github.com/vyanhursky/defjam-ffny-fighter-workshop/actions/runs/42640408538

The runtime PR integrates current research fixes; its hosted CI is still being
qualified. The original in-game evidence above remains macOS-only and predates
that base integration. Hosted game-free checks do not replace gameplay tests.

Native package CI now also executes the relocated frozen authoring helper with
a synthetic selected runtime and a16x16 DXT5 portrait encode. This verifies
bundled runpy/Pillow plugins and DDS support on each OS/CPU without game data;
it remains separate from native CAF gameplay acceptance.
