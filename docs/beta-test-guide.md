# Local beta test guide

These steps cover Workshop 0.1 Beta 2. Project exports pair with Recomp
**1.2.0 beta 2** or a compatible source checkout. Stable 1.2.0 lacks its authoring
tools. Check Game setup's per-version feature list before export/performance work.

## Terminology

A Story profile includes career progress/currency; a project is a portable fighter
authoring file with looks called outfits. The game version compiles its export
recipe. See the shared [terminology](terminology.md).

## Story profile checks

1. Use separate copies of your saves, with access to the original `extracted`
   directory. **Close the game before saving in Workshop.** On Home, choose
   **Story character editor** and configure the copied data in Game setup.
2. Select an existing fighter. Rotate/zoom and compare body, face, clothes, hair
   and tattoos with the game. Test Front/Back/Fit, the three poses and four lighting
   choices. Wardrobe-inspired and Relaxed are approximate preview deformation.
3. Browse body, skin, facial presets, clothing/hair/tattoos, color and fitting.
   Browsing previews; **Equip** stages. Try rapid changes and check the latest
   selection wins. No clothes temporarily hides apparel/accessories. Preview
   controls and uncommitted try-ons never change saves or exported settings.
4. In **Stats & cash**, test five training stats (0–50), cash (0–10,000,000), and
   development points (0–100,000). Currency limits are conservative verified
   policies, not universal format maxima.
5. In **Moves**, apply one to three distinct CAF styles and four Blazin' choices.
   Check style bonuses while preserving earned bonuses. Retail movesets ship,
   but direct Story edits require the compatibility acknowledgement and a game
   with the Story adapter. See [movesets](retail-movesets.md).
6. Test Pending Changes, Undo/Reset, Ctrl+S, Ctrl+Z and unsaved-exit cancellation.
   Export a complete `.djprofile`, duplicate to a fresh ID and compare Story
   progress. Save only a copy; check its backup and completion summary.
7. Restore a backup from the left panel; verify the replaced save was backed up
   first. Import the export into a second disposable data folder. Check collision
   refusal, fields and appearance after reopening.
8. Launch the compatible game on disposable saves. Load Story, inspect wardrobe,
   save normally, quit and reopen. Record exact game build and actions. Editor
   and codec tests alone do not prove native gameplay acceptance.

## Project and retail checks

Exercise Home's **Fighter from a Create-a-Fighter**, **Fighter from a retail
fighter**, and **Retail fighter editor**, including New/Open, recent projects,
Home round trips and discard cancellation. Follow [CAF projects](fighter-projects.md)
and [retail projects](retail-fighter-projects.md) to save/reopen metadata, outfits,
portraits, HD atlases and menu art. Save As keeps identity; creating a new fighter
generates a new pack identity. Project files exclude Story progress.

Face sliders/template import are experimental project features. Compare Apply,
Undo and reopen. Visit Entrance or AI first and verify catalogs load automatically;
check inline failure/retry and older-runtime errors. Use the pinned export
checklist, follow failing checks, and confirm staged edits save before the chooser.
Export a fresh ZIP, inspect the
summary, then install in the matching game's **Mods → Fighters** and test gameplay.

For retail replacements/extra outfits, use the
[dedicated walkthrough](retail-overrides-outfits.md). Import an original body
using the empty viewer's action; preview should load automatically once. Check
the compact header, full IDs, collapsed start controls and keyboard tabs at
1440×940 and 1100×760. Extra outfits share target combat identity and count
toward its three-outfit total.

## Limits and reporting

Existing Xbox-based Recomp profiles only. Profiles without a Story fighter stay
read-only until the game creates one. Unknown save bytes/appearance encodings
are preserved; unverified right-wrist encodings remain unavailable. Project
assets do not belong in unknown save fields. Arbitrary topology, granular moves
and custom animation authoring remain deferred. CAF original-track playback has
limits; retail preview remains static.

Report workflow, action, expected/observed result and both Workshop/game versions.
The workspace's `logs/desktop.log` records packaged startup errors. Keep saves,
assets, projects and captures private in public issues. Historical platform
checks and this release's narrower acceptance are distinguished in
[platforms](desktop-platforms.md), [release notes](releases/v0.1.0-beta.2.md)
and [PROGRESS](../PROGRESS.md). Native CI startup does not replace hands-on editor
checks or native gameplay acceptance on each platform.
