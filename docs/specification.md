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
