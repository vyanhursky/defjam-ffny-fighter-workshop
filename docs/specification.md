# Agreed product scope

Owner decisions, 2026-11-07.

## Beta

- A packaged desktop application with its own window on Windows, macOS and Linux.
- Select a Recomp data directory; discover and choose existing profiles.
- Render the saved CAF's actual appearance, including supported body, hair,
  clothing, jewelry and tattoos. Expose all retail CAF items, including locked
  items. Preserve Story progression when editing appearance.
- Display and edit character stats within normal game caps, cash and development
  points within verified limits. Distinguish development points from other points.
- Display fighting style and allow proven CAF style combinations. Named fighter
  movesets are conditional on verified profile-only support; defer anything that
  requires a runtime mod.
- Commit changes to the selected profile, export/import a complete profile, or
  duplicate to a new named profile while preserving Story progress.
- Backups, undo/reset, change review, collision refusal and stale-file detection.
- Standalone public repository named `defjam-ffny-fighter-workshop`. Build and test
  locally and perform game import/export functional acceptance. Development
  source publication on `develop/0.1` is authorized; owner hands-on review remains
  pending before a packaged release.

Fresh profile creation, console/emulator compatibility and fighter-only presets
are outside this beta's required scope.

## Preview foundation

Modding Tools PR #5, merged at `9bb5b834b6c39e82f69ee93035a0803b1b62a8d3`,
provides static CAF assembly, source body-build morphs, four-atlas composition,
skin/hair palettes, shop clothing/color/style joins and tattoo placements.
Reuse its attributed source while removing its requirement for the production
art-review corpus. Derive a private asset cache directly from Recomp game data.

Its default-face-only rendering and incomplete clothing compatibility are
explicit implementation gaps. A saved face must not silently be replaced with
the default face. Retail body-size labels must be mapped from game evidence.
Preview shader approximations must be disclosed. New face-editing controls beyond
the referenced viewer are not required, but faithful loading of existing faces is.

## Validation gates

1. Save discovery and size/signature validation; unchanged codec round-trip.
2. Establish each editable field from game behavior/code and controlled fixtures.
3. Transactional persistence, backups, stale-source rejection and unknown-byte
   preservation; full-profile export/import and collision-safe duplication.
4. Profile-to-appearance translation and representative native comparisons.
5. Native load, edit, save, quit and reload; export to a separate test data root,
   import and play. Verify appearance, stats, cash, development points, fighting
   styles, duplicated identity and Story progress. Hash originals before/after.
6. Owner testing and native Windows/macOS/Linux packaged-app acceptance.

## Roadmap (deferred)

Granular movesets, animation player, custom meshes/textures, custom animations,
custom fight voices and fighter modpack authoring. Do not investigate the separate
Custom Fighter R&D worktree as part of this beta.

## Approved four-slot Blazin' editor — 2026-11-09

The owner requested editable assignments, analogous to fighting styles, for both
Story CAFs and standalone CAF projects. Offer all verified original-game Blazin'
moves, including character moves, without style or shop-unlock filtering. Allow
duplicates. Stage all four assignments together; use normal Undo/Reset, named
change review, profile backup and project save/copy/export. Existing unknown
references must remain untouched until explicitly replaced.

The menu consumes provider-qualified stable keys and named source groups, not
native row ordinals. This leaves a route for future custom Blazin' providers.
Original native saves and CAF v2 currently encode retail references only; actual
custom animation resources require an explicit future contract/runtime capability.
Animation playback in the editor remains deferred.

## Approved complete fighter UI artwork — 2026-11-09

Extend roadmap fighter modpack authoring with editable selector/loading portraits,
stylized titlecards, result icons and normal/selected grid icons. Audit retail
Method Man/Blaze layouts rather than treating one portrait as all presentation.
Support six master roles and all 24 native 2/3/4-player variants, shared default
art with per-outfit overrides, exact embedded PNGs and compatible HD output.
Keep UI donor/layout independent of combat identity, preserve old projects and
Story profile workflows, and validate complete packs through the shared runtime.
Use original Pockets placeholders when the requested Tupac generation is refused.
Source PR updates are authorized; artwork, saves, captures and game binaries stay
private. This does not authorize a packaged release or merge.

## Approved multi-outfit fighter projects — 2026-11-09

Extend roadmap fighter modpack authoring with one stable fighter and one roster
entry offering up to three outfits, like the original Blaze and D-Mob selectors.
Project version 3 retains the default appearance at the root and adds named
outfits with stable IDs. Stats, styles and Blazin' assignments are shared;
appearance, imported atlases and portraits are outfit-specific. Existing project
versions and Story profile workflows retain their contracts.

Project controls copy, rename, switch and remove additional outfits. Switching
preserves staged edits; Undo/Reset, change review, save/copy/variant and export
cover the complete project. Each appearance validates its own texture bindings.
Export declares CAF v3, reuses normal typed portrait resources and validates the
whole pack with the companion runtime before publishing its ZIP. The native
selector chooses outfits independently per participant without adding progress
identities. Portrait aliases are temporary UI paths, never fighter/save IDs.
Native gameplay, cancellation and rematch acceptance remain separate from codec
and static model tests. This does not change the original Story save format or
add arbitrary outfit counts/custom animation support.

## Texture-mod fighter pilot — 2026-11-09

Owner requested recovering an existing texture-mod CAF, proving its stock body
and retail moveset in-game, then restoring its textures to match the HD fighter
and portrait packs. The first outfit is the saved shirtless outfit. Work uses
isolated source/data workspaces and preserves the released profile editor.

The enabling roadmap feature is custom textures and fighter modpack authoring:
hash-bound atlas assets, explicit UV/alpha-preserving mapping, preview and
fighter-specific runtime ownership. Granular moves and custom animation are
not required to reproduce the existing retail CAF style combination.

Experimental read-only PS2 snapshot recovery is documented in
[PS2 CAF recovery](ps2-caf-recovery.md). Only independently validated fighter
fields are eligible for a new project; no Story-save conversion is implied.

## Approved next milestone — 2026-11-08

Standalone portable fighter projects, conversion from existing CAFs and export
to the public Custom Fighter runtime contract, including stable pack/fighter
identity, names, author/version/description/credits and supported presentation.
Reuse the existing runtime/compiler and validate the generated pack there.
Test actual native selection/combat on research/custom-fighter-mods using
disposable saves. Projects exclude Story progression and currency; existing
profile export remains available. Required runtime extensions must be explicit,
with their actual tested source recorded. No merge, push or release is implied.
