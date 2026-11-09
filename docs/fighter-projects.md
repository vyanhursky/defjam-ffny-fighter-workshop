# Standalone fighter projects (development preview)

This workflow is under development after 0.1 Beta 1. It requires the matching
Custom Fighter runtime extension; the released Beta 1 editor/game do not provide it.

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
Individual move authoring, custom clothing/model/texture import and animation
playback are later milestones. CAF export currently rejects unsupported
appearance encodings and combinations with sourced non-portrait components.
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
