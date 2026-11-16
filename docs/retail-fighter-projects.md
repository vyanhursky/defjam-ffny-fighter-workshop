# Retail fighter studio

Workshop 0.1 Beta 2 includes two Home workflows: **Fighter from a retail fighter**
for a new standalone fighter, and **Retail fighter editor** for an existing
fighter's appearance or extra outfit. Use **New** to start or **Open** to resume
its portable project. Neither workflow writes Story saves.

In **Game setup**, select your Recomp folder, a compatible game version and the
data folder containing extracted files. Use Recomp **1.2.0 beta 2** or a
compatible source checkout; stable 1.2.0 lacks the required authoring commands.
The runtime verifies the original database and supplies the fighter catalog.

## Terminology

A Story profile includes game progress; a project holds fighter settings; an
outfit is one selectable look. The game version compiles the export recipe.
See the shared [terminology](terminology.md).

## Create and export

For replacing an existing retail appearance or adding an outfit to its original
clothing selector, follow the [retail override/outfit walkthrough](retail-overrides-outfits.md).
The steps below describe a new standalone fighter.

1. Create a fighter from a retail donor, open a portable `.ffnyfighter` project,
   or import one fighter from an ordinary pack folder. Imported packs must have
   no dependencies. A single-target appearance override is also supported;
   multi-target/global override packs remain refused. Import follows hash-bound JSON references
   and embeds the selected resource files; it does not install or enable a pack.
2. One starting fighter supplies combat/body/UI defaults. Once started, the
   setup block collapses; **New…** reopens it. Under **Advanced: mix donors**,
   choose a different **Combat donor** for the original moveset and inherited native
   health, speed, toughness and charisma. These are 0–100 retail values, distinct
   from CAF training values. Applying the donor clears explicit stat overrides.
3. Use **Import original body** in Fighter or the empty viewer. **Body donor**
   under Advanced selects a different body to import; it does not label the origin
   of a previously imported body. You can also keep an imported owned appearance.
   Original meshes, textures and facial data come from the player's verified
   archive. Four-character texture names are scoped to the project, including
   native injury textures, so their global shape names do not collide.
4. Select supplied voice, Blazin', intro and victory resources, or choose
   **Inherit from donor** for a fallback. Resource names and source bytes remain
   in the project. The combat family is declared at export; the runtime still
   checks actual rig topology/permutation, skin palettes, render templates,
   graph rig identities, motion/event templates and every file hash. Changing a
   label does not adapt incompatible data, and failed compilation publishes no ZIP.
5. Body import automatically refreshes the static 3D preview and texture shapes.
   Use **Refresh 3D preview** after later changes. Orbit/zoom, Front/Back/Fit and Wireframe inspect
   the source pose. Collapsed source placeholders, untextured helpers and sparkle
   are omitted from this preview. Runtime appearance data is unchanged. It does
   not play animations or reproduce native material shading/injury switching.
6. Under **Textures**, choose an original shape and import a complete RGB PNG at
   native, 2× or 4× dimensions (32–2048px, at most 16 MiB). The matching runtime
   admits `eagl-appearance-png-1`. It retains native UV dimensions, controls and
   exact material alpha, compiles an indexed/BGRA/DXT fallback, and emits source
   HD RGB with nearest original material alpha. Invalid layouts and alpha changes
   are refused. Native color quantization is separate from the source HD raster.
7. Import six master UI images or 24 player-layout variants for selector/loading
   portraits, titlecards, result icons and grid states. UI donor and 1×/2×/4×
   output are independent of combat. Change the UI donor in Fighter's Advanced
   disclosure, then apply UI settings in UI artwork. All roles share the existing typed PNG
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

Retail projects have one current schema with an optional deployment purpose/target;
earlier files remain readable. CAF projects and profile workflows stay separate.
Generic Blender/GLB mesh reimport, arbitrary sculpting and animation authoring/
playback remain deferred in the retail studio. An extra-outfit project adds one
appearance to a retail fighter within its three-outfit total, sharing combat,
voice and progress rather than creating another public roster identity.

Original and generated artwork, imported projects and packs, decoded previews,
saves and captures remain private. Export validation does not prove native gameplay or platform acceptance.
See [Beta 2 qualification](releases/v0.1.0-beta.2.md) and [PROGRESS](../PROGRESS.md).
