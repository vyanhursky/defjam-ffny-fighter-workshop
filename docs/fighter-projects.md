# Fighter projects from a Create-a-Fighter

Workshop 0.1 Beta 2 includes portable fighter projects and validated mod export.
Use the matching Recomp **1.2.0 beta 2** build or a compatible source checkout.
Stable Recomp 1.2.0 lacks these authoring commands. **Game setup** lists what the
selected build supports. Compiler validation and native gameplay acceptance are
separate; tested scope and limits are recorded in [PROGRESS](../PROGRESS.md).

## Terminology

A Story profile holds game progress; a project holds a fighter; an outfit is one
of its looks. The game version compiles the export recipe. All guides use the
shared [terminology](terminology.md).

## Start, save and export

1. On Home, choose **Fighter from a Create-a-Fighter → New**. In **Game setup**,
   select the Recomp folder, compatible game version and data folder containing
   `extracted` and `save`. These choices are remembered. The first launch builds
   a private wardrobe cache and can take several minutes.
2. Select the Story fighter to start from, use the start banner's create action,
   and choose a `.ffnyfighter` destination. Staged fighter changes are included;
   the profile stays untouched. Home's **Open** or **Open project** reopens an
   existing project independently of the source save.
3. Edit using **Appearance**, **Textures**, **Stats & cash**, **Moves**, **Voice**,
   **Entrance & victory**, **AI**, **Menu artwork**, and **Details & export**.
   Cash/development points belong to Story profiles and are disabled in projects.
   **Save project** writes all staged changes to the project file.
4. In **Details & export**, set the name, author, pack/fighter IDs, semantic version
   (`major.minor.patch`), description, credits/license and presentation donor.
   Keep IDs stable across revisions. **Save project as…** preserves identity;
   **Save as a new fighter (new pack ID)…** at the bottom creates a new identity.
5. Capture the current view or import a portrait in **Textures**. Equip the
   intended clothing first. Without imported art, the retail donor supplies
   placeholders. Pose and lighting affect the capture, never fighter settings.
6. Use the pinned **Export mod…** action. Its readiness checklist covers the
   project, game version, details, portrait fallback, outfits and unsaved drafts.
   Follow a failing check to its controls. Confirming saves pending project edits
   before the ZIP chooser. Choose a fresh ZIP destination; the remembered game
   version validates the whole pack and all menu layouts before writing it.
7. In the matching game's launcher, open **Mods → Fighters**, add the ZIP and
   enable it. Test selection, outfits and gameplay on disposable saves. Exporting
   does not install or activate a pack.

Projects exclude career progress, currency, inventory, save containers and private
source paths. Original extracted assets are still needed for preview/export.
Uncommitted try-ons and preview visibility do not change exported fighter data.
Undo, Reset and Pending Changes cover the staged project; closing asks before
discarding edits. Save refuses external changes and Save As refuses collisions.
Earlier projects remain readable without modifying their files until Save.
Pending Changes is pinned above Save and Export; expand it to inspect the list.
Ctrl+S saves and Ctrl+Z undoes; tooltips and Messages list these shortcuts.

## Outfits

The left **Project** panel shows the filename/folder and all outfit operations:
select, rename, **Copy as new outfit**, or remove an additional outfit. The
selector above the viewer mirrors the selection among up to three looks. The
default outfit is retained. Switching preserves
staged changes; Save writes the collection. Stats, moves and performance settings
are shared. Appearance, atlases, portrait, menu artwork and face sculpt can vary.
The game shows one fighter cell with its original clothing-choice menu.

## Textures and faces

In **Textures**, each sheet has Import/Revert controls. Import complete square
**256, 512, 1024 or 2048 px** PNG atlases, at most **16 MiB** each. A–D are the
composed CAF atlases; D1/D2 are facial injury variants. PNG bytes remain unchanged;
preview/export use imported RGB and original material alpha.

Changing body, face or wardrobe keeps imported art and rebinds it to the look.
Geometry/UV changes can affect fit; the editor does not repaint or remap it.
Clear/revert is staged. Save, copy and new-identity variants retain art. HD output
uses the matching game's HD system; static preview does not simulate injury
transitions or every native material effect.

**Appearance** offers original facial presets. Advanced proportion sliders and
template OBJ head import are experimental and belong to projects, never unknown
Story-save bytes. Template import preserves topology, UV and rig contracts.
See [face authoring](face-authoring.md) for qualification and limits.

## Moves and performance

**Moves** selects a CAF combination or an original retail fighter's full moveset.
Four Blazin' selectors use the original database's full pool, independent of
styles/unlocks. Duplicates are allowed. Pick all four and **Apply Blazin' moves**.
A project's **Use inherited moves** removes its explicit assignments. Unknown
saved choices are preserved until replaced; partial project assignments are
refused. Creating a project resolves verified saved identities. See
[retail movesets](retail-movesets.md) for direct Story-save compatibility.

Opening **Voice**, **Entrance & victory**, or **AI** automatically loads the
remembered game's catalogs. Loading and failures appear in that tab; use Retry
or Game setup after a failure. Voice also offers **Reload voice & animation
catalogs**. Select a voice bank,
import mono PCM16 WAV clips, choose original entrances/victories, and edit CPU
personality. Supported original tracks play in the viewer; unsupported codecs,
facial animation and native blending remain outside preview scope. These
overrides are project features. See [performance editor](performance-editor.md).

## Menu artwork

Import transparent PNGs for six master roles: selector portrait, loading portrait,
result icon, titlecard, normal grid and selected grid. Advanced slots target 24
individual 2/3/4-player layouts. Importing a master replaces covered local
overrides; clearing a role restores inheritance. Preview identifies its source.
The default outfit supplies shared art; other outfits can override roles/settings.

Choose a named UI layout donor independently of combat; choices come from the
connected game's catalog. **Import complete retail UI
set** reads placeholders from your own files through the selected runtime. No
extracted art is bundled. PNGs must be 32–2048 px per side, at most 4 MiB each.
UI imports share a 48 MiB / 64 million decoded-pixel budget. Native, 2× or 4×
output retains alpha/padding and original movie layout/actions; resampling cannot
invent detail. Exact donor canvases preserve framing; other images are fitted
or cropped for their role. Story saves do not accept UI imports.

## CLI

```sh
defjam-caf project --data /path/to/data --profile DEMO --out Demo.ffnyfighter
defjam-caf export-mod Demo.ffnyfighter --data /path/to/data \
  --runtime /path/to/compatible/runtime --workspace /path/to/private/workspace \
  --out Demo.zip
```

Experimental [PS2 snapshot recovery](ps2-caf-recovery.md) creates a project from
verified fighter fields; it does not convert Story saves. Arbitrary clothing/mesh
import, individual move authoring and custom animation authoring remain deferred.
Keep source art, projects, saves and captures private unless you can publish them.
