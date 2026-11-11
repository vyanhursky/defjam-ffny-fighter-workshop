# Standalone fighter projects (development preview)

This workflow is under development after 0.1 Beta 1. It requires the matching
Custom Fighter runtime extension; the released Beta 1 editor/game do not provide it.

On **Project & mod**, **Fighter outfits** switches between up to three named
outfits. **Copy as new** clones the selected appearance, textures and portrait;
edit the copy's clothing and import matching complete atlases, then capture its
own portrait. **Remove** deletes additional outfits; the first outfit is kept.
Switching preserves staged changes. Stats, fighting styles and Blazin' moves
apply to every outfit. Undo/Reset and Save cover the complete project.

A fighter project is one schema (`ffny-fighter-project-7`) whose sections are all
optional: finishers, a retail moveset, textures, a portrait, an outfit collection,
UI artwork, face sculpts and performance settings. Projects saved by earlier
builds hold a subset of those sections, so they open unchanged and are saved under
the current schema. Every export uses the one recipe format `caf-fighter-1`. The
game shows one roster cell, then its original clothing-choice
menu. Each outfit has its own selector/loading/result portrait. One fighter
identity retains shared unlock/progress ownership. Existing single-outfit
projects keep their earlier formats until outfit controls upgrade them.

1. Open your Recomp data directory and select an existing Story fighter.
2. On **Project & mod**, choose **Create project from this fighter** and save a
   `.ffnyfighter` file. Staged fighter changes are included. Your original profile
   remains untouched.
3. Edit appearance, training stats and retail fighting styles as usual. **Save
   project** writes the project. **Open project** reopens it independently of the
   source save; original extracted game assets are still needed for 3D preview
   and mod export. Cash and development points belong to Story profiles.
4. Set the display name, author, stable pack/fighter IDs, semantic version,
   description, license/credits and presentation donor. Keep IDs stable across
   revisions of the same fighter. **Save project as** makes a copy with the same
   identity; creating a new project generates a new pack identity.
5. Optionally use **Capture current view as portrait** or import a PNG. Equip
   clothing before capturing, show the full outfit, and frame the fighter with
   the view controls. The project embeds the PNG. Without one, presentation
   artwork inherits the retail donor.
6. Choose **Export Custom Fighter Mod**, select the compatible runtime source
   checkout, and choose a new ZIP destination. Export runs that runtime's shared
   authoring API and complete native pack/menu compiler against your local dump.
   It writes the ZIP only after validation succeeds.
7. In the **matching research runtime's** launcher, install the ZIP under
   **Mods > Fighters** and enable the pack. Development testing should use a
   disposable profile. The public research branch documents the existing
   [launcher/profile workflow](https://github.com/vyanhursky/DefJamFFNY-recomp/blob/research/custom-fighter-mods/docs/fighter-mod-support.md#local-m4-launcher-workflow);
   the companion CAF extension must also be built into that runtime.

Projects contain five training stats, one to three distinct retail styles and
CAF appearance selections/colors. Style bonuses are rebuilt independently;
career bonuses and Story-derived charisma are not copied. Projects exclude
Story progress, currency,
profile containers, inventory and source paths. Preview-only clothing try-ons
and visibility are excluded from fighter data; pose/lighting affect a captured
portrait only. Unsaved details and portraits participate in the close/discard
check. Saving refuses external changes and Save As refuses collisions.

The ZIP uses the existing `fighter-registry-draft-1` contract with a
`caf-fighter-1` resource. It contains `fighters.json`, a hash-bound `fighter.json`,
a README and credits/license text, plus six native portrait rasters when a PNG
is selected. The player's original files supply the CAF meshes and textures;
the export contains no Story profile or compiled game executable. Portraits
are converted through locally verified original UI templates. 

Voice, AI and unmodified presentation inherit the selected retail donor.
Project v7 can override these independently in the [performance editor](performance-editor.md).
Individual move authoring, custom clothing/model import and animation
playback are later milestones. Native atlas import is described below. CAF export currently rejects unsupported
appearance encodings and combinations with sourced non-portrait components.

### Complete UI artwork (development)

Open **UI artwork** in a standalone project. Import transparent PNGs for six
master roles: selector portrait, loading portrait, result icon, titlecard, normal
grid icon and selected grid icon. A master fills all relevant layouts. The 24
advanced roles provide independent selector/result portraits, selector/result/
loading titlecards, loading portraits and both grid states for 2, 3 and 4 players.
Importing a master replaces its local advanced overrides; clearing a local role
restores inherited artwork. The preview identifies the source of the selected art.

The first outfit supplies shared defaults. Other outfits inherit those defaults
and can override any role or UI setting independently. Undo, Reset, change review,
Save, copy and variant creation include all art. Opening an older project alone
changes nothing on disk until you save it.
Story profiles retain their original presentation and do not accept these imports.

Choose the retail UI layout/placeholder donor independently of the combat donor.
**Import complete retail UI set** reads 24 PNGs from your own extracted game via
the compatible runtime. Loading close-ups and titlecards remain separate assets.
Grid placeholders derive from that donor's result icon; import distinct normal
and selected grid art when desired. Retail placeholders are original game art,
not an HD restoration. No extracted art is shipped with Workshop.

PNGs must be 32–2048 pixels per side, at most 4 MiB each, with visible content.
The project admits at most 48 MiB / 64 million decoded pixels across UI imports.
Source PNG bytes are embedded unchanged. Exact donor canvases at 1×, 2× or 4×
retain their layout; other images are fitted inside the original covered region,
with square result/grid crops. Use exact per-layout canvases for precise framing.
Original movie actions, geometry and material controls are preserved by export.

Choose native, 2× or 4× texture output. HD tiles are resampled directly from the
imported source, retain alpha/padding, and activate automatically after selected
texture packs through a verified, temporary fighter UI layer. This preserves
high-resolution source detail; increasing the output scale cannot invent detail.
The exported `eagl-portrait-png-1` resources require the matching runtime update.
Old six-part portrait exports remain supported.
Export compiles every layout before publishing the ZIP, without installing it.

### Native atlas import and saved finishers (development)

Project version 2 embeds native 256×256 PNG atlases and preserves the four saved
retail Blazin' assignments as SODB record identities. Existing version 1 projects
remain readable and keep their original fields. Creating a project from a save
now resolves its finishers against the original game database; missing or
unverified references are refused instead of silently discarded. PS2 snapshot
recovery is an [experimental separate input path](ps2-caf-recovery.md).
All four finisher slots must be concrete or all absent; partial project
assignments remain unsupported until their native semantics are verified.

### Editing Blazin' assignments

The **Blazin' moves** tab offers four named selectors populated from the player's
original game database (82 moves in the verified dump). Character finishers and
CAF moves share the full pool, independent of styles and Story unlocks. Duplicate
choices are allowed. Pick all four, then **Apply Blazin' moves** to stage them.
Review slot/name changes, use Undo or Reset as needed, then Save. Browsing a
dropdown alone does not alter the fighter. Supported source-track playback is available in the Animation tab; see the performance editor limits.

For a Story CAF, saving updates only its four assignment references, with the
normal original backup and stale-save protection. Creating a standalone project
from that fighter retains the edited moves. For a project, saving retains four
stable retail record identities, and export resolves them through the matching
CAF v2 runtime. **Use inherited moves** removes a project's explicit override;
it is unavailable for Story profiles. Saving/copying/creating variants retains
assignments; changing them does not invalidate imported outfit textures.

Missing assets disable the catalog. Missing/unknown saved references display an
unavailable/unassigned placeholder and remain untouched until all four are
explicitly replaced. Names/order come from the local database. The UI consumes
provider-qualified stable keys and source groups, leaving room for future custom
move catalogs. Custom animations are not currently accepted by native profile or
CAF v2 export; that requires a versioned resource/runtime extension, not a raw
animation index in the menu.

### Atlas workflow

Under **Project & mod → Texture atlases**, choose an atlas and import its PNG.
The preview uses its RGB while retaining the original material alpha. A–D are
the four composed CAF atlases; D1/D2 are native facial injury variants. Import
complete flattened atlases for the selected outfit. The project binds them to
its current appearance choices and colors. Changing body, face or wardrobe
options preserves the imported PNG bytes and updates that binding. Imported RGB
takes precedence over in-game tattoo/clothing artwork on those atlases until
explicitly cleared or replaced. Geometry/UV changes can affect the art's fit;
the editor does not automatically repaint or remap the PNG.
Clear is staged, Reset restores saved art, and Save project/Save project as
include all assets. Variant projects retain art and finishers with a new identity.

The matching runtime must support `caf-fighter-1` and reads these through the
extras section of its hash-checked `fighter-caf.bin`. Export includes declared PNGs and validates the
complete pack through that runtime. The game creates independent owned native
bitmaps for each CAF, preserves alpha, handles its Xbox Morton layout, and uses
the original visual teardown. It does not enable a global content-hash texture
replacement. Existing profile export/import and version 1 recipes are preserved.

Current atlas admission is 1×/256×256. HD restoration, higher-resolution atlas
admission, arbitrary custom meshes and animation playback remain later work.
Source PNGs are stored unchanged; RGB integration is separate from art approval.
Export validation is separate from in-game acceptance and does not install or
activate the ZIP. Use the compatible research runtime's local mod workflow.

CLI equivalents:

```sh
defjam-caf project --data /path/to/data --profile DEMO --out Demo.ffnyfighter
defjam-caf export-mod Demo.ffnyfighter --data /path/to/data \
  --runtime /path/to/compatible/runtime --workspace /path/to/private/workspace \
  --out Demo.zip
```

Development runtime: based on public `research/custom-fighter-mods`, with the
companion CAF recipe and portrait API changes. Its shipping gates and save
isolation requirements remain in force. Native validation evidence and remaining
qualifications are recorded in `PROGRESS.md`.
