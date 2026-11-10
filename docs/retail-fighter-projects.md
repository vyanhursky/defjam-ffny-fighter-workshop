# Retail fighter studio (development)

Open **Retail fighter studio** from the CAF editor's data strip. This separate
workspace preserves the current profile/CAF session and never writes Story saves.
Select the Recomp data directory and a matching development runtime checkout.
The runtime verifies the original database and supplies the 75-fighter catalog.

1. Create a fighter from a retail donor, open a portable `.ffnyfighter` project,
   or import one fighter from an ordinary pack folder. Imported packs must have
   no dependencies or global overrides. Import follows hash-bound JSON references
   and embeds the selected resource files; it does not install or enable a pack.
2. Choose the **combat donor** for the original moveset and inherited native
   health, speed, toughness and charisma. These are 0–100 retail values, distinct
   from CAF training values. Applying the donor clears explicit stat overrides.
3. Import a **body donor** independently, or keep an imported owned appearance.
   Original meshes, textures and facial data come from the player's verified
   archive. Four-character texture names are scoped to the project, including
   native injury textures, so their global shape names do not collide.
4. Select supplied voice, Blazin', intro and victory resources, or choose
   **Inherit from donor** for a fallback. Resource names and source bytes remain
   in the project. The combat family is declared at export; the runtime still
   checks actual rig topology/permutation, skin palettes, render templates,
   graph rig identities, motion/event templates and every file hash. Changing a
   label does not adapt incompatible data, and failed compilation publishes no ZIP.
5. Refresh the static 3D preview. Orbit/zoom, Front/Back/Fit and Wireframe inspect
   the source pose. Collapsed source placeholders, untextured helpers and sparkle
   are omitted from this preview. Runtime appearance data is unchanged. It does
   not play animations or reproduce native material shading/injury switching.
6. Under **Textures**, choose an original shape and import a complete RGB PNG at
   native, 2× or 4× dimensions (32–2048px, at most 4 MiB). The matching runtime
   admits `eagl-appearance-png-1`. It retains native UV dimensions, controls and
   exact material alpha, compiles an indexed/BGRA/DXT fallback, and emits source
   HD RGB with nearest original material alpha. Invalid layouts and alpha changes
   are refused. Native color quantization is separate from the source HD raster.
7. Import six master UI images or 24 player-layout variants for selector/loading
   portraits, titlecards, result icons and grid states. UI donor and 1×/2×/4×
   output are independent of combat. All roles share the existing typed PNG
   compiler and verified per-launch HD layer. Conflicting native texture hashes
   remain errors, even when different HD sources quantize to identical fallbacks.
8. Apply details, review staged changes, Undo/Reset, Save or Save As. Metadata
   drafts participate in dirty/close protection, and invalid drafts refuse Save.
   Original-source files stay untouched. Embedded asset/art budgets and the
   portable file-size limit prevent saving a file that cannot be reopened.
9. Export **Custom Fighter Mod** to a fresh ZIP path. The runtime compiles the
   complete ordinary pack and every menu layout first. Export excludes unused
   resources and assets, Story saves, private source paths and game executables.
   Native gameplay, resource cleanup and art approval remain separate checks.

Retail projects use `ffny-retail-fighter-project-1`. Existing CAF project versions
and profile workflows keep their existing formats. This milestone implements
retail/owned fighter modpack authoring and texture import. Generic Blender/GLB
mesh reimport, sculpting, animation authoring/playback and arbitrary retail
multi-outfit collections remain deferred. A second outfit for the private pilot
is a later task, not a second roster identity created implicitly here.

Original and generated artwork, imported projects and packs, decoded previews,
saves and captures remain private. This development feature does not authorize
a merge, packaged release, asset publication or native platform claim.
