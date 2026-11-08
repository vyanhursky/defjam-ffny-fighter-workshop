# Progress and handoff

## Status — 2026-11-07

Local beta source is published at
https://github.com/vyanhursky/defjam-ffny-fighter-workshop on `develop/0.1`, the
default branch. The owner approved the four README screenshots and authorized
the first packaged prerelease, v0.1.0-beta.1. Publication is gated on the tagged
source's native CI and checksum/provenance verification; the release page records
publication state. Broader owner/game acceptance remains ongoing. Saves and
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
- Initial packaged preview and actual stats-panel editing/undo were observed
  through Windows UI automation. The owner-test handoff uses copied profiles
  and a local shortcut. Full owner acceptance remains pending.

## Decisions and limits

Existing Recomp profiles only, full-profile transfer and Story-preserving
replication. New IDs conservatively use1–7 uppercase letters/digits. No fresh
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

## macOS/Linux compatibility — 2026-11-07

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

## Installer data default and Recomp icon — 2026-11-07

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

## Native CI publication — 2026-11-07

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

## Native CI results and handoff — 2026-11-07

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

## PR #1 merged — 2026-11-07

Owner approved and PR #1 merged into `develop/0.1` at `5bbcccc`. The final PR
head `3878375` passed all four native CI jobs in run 42445695324: Windows x64,
macOS arm64/x64 and Linux x64. The merge preserves the tested source tree.
The default branch now runs native package CI on pushes as well as PRs.

The local checkout returns to `develop/0.1`; the merged feature branch is
removed after synchronization. No tagged release was created. Next work remains
owner acceptance and the broader native editor/game checks documented above;
CI package/startup evidence does not replace those checks.

## README screenshot approval — 2026-11-07

Owner requested four examples for the develop/0.1 README, with candidate review
before publishing: main window, stats/cash, fighting-style combinations and
clothing. Four actual Qt window captures were prepared from source 418d08d,
using a disposable DEMO profile and a generic temporary data path. Each capture
is 2880 x 2076; no pixel alterations or UI text replacements were applied.
The original source profile's hashes are unchanged.

The owner approved all four exact candidates. They are committed under
docs/media with SHA-256 pins and an artwork exception in AGENTS.md; the main
README shows the approved gallery. No original assets or saves are committed.

## 0.1 Beta 1 release authorization and handoff — 2026-11-07

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
