# Retail appearance overrides and additional outfits

The retail studio's **Project purpose** chooses between a separate fighter,
replacement appearance for an existing retail fighter, or an additional outfit
in that fighter's original clothing selector. Choose the retail target before
importing its original appearance and a replacement texture PNG.

Save the portable `.ffnyfighter` source project, then export its mod ZIP. Import
and enable the ZIP through the game's ordinary mod installer. The source project
retains the supplied native model resources, authored PNGs and metadata for
further editing. An exported single-fighter ZIP can also be imported into the
studio after extracting the ZIP. Export itself does not install or activate the pack.

## Create a replacement or an extra outfit

1. Open **Retail fighter studio** from the CAF editor. Select **Game data…**
   and **Runtime…** for a matching development runtime with retail outfit support.
2. Under **Original fighter**, choose the retail target, for example **Pockets**.
   Set **Project purpose** to one of these choices, then click **New from retail fighter**:
   - **Override existing retail appearance** replaces that fighter's appearance
     without adding an outfit or another roster entry.
   - **Add outfit to existing retail fighter** keeps the original and adds a
     choice to its existing clothing selector.
3. For an already-open project, set **Project purpose** and **Existing fighter**
   in the center panel, then click **Apply project purpose & target**.
4. Choose the matching **Body donor**, then **Import original body**. Do this
   before painting: importing a body again replaces the appearance and clears
   its previous texture imports. Click **Refresh 3D preview** to load the model
   and populate the texture-shape list.
5. In **Textures**, select the relevant **Texture shape** and **Import RGB PNG…**.
   For the Pockets pants example, use his complete **A001** atlas with the pants
   recolored. Keep the original UV layout; supported sizes are native, 2× or 4×,
   within 32–2048 pixels and 16 MiB. Refresh the preview to inspect the result.
6. Fill in the project details and click **Apply project details**. Use distinct
   **Pack ID** values for separate replacement and extra-outfit test packs.
7. Click **Save project** to keep an editable `.ffnyfighter`, then
   **Export Custom Fighter Mod…** to a new ZIP filename. Compilation validates
   the resources before creating the ZIP.

The same procedure works with other compatible retail fighters. Each outfit
project supplies one additional appearance; the total native limit still applies.

## Install and verify in the game

1. In the matching Recomp build, open **Mods > Fighters**, import the exported
   ZIP, enable the pack and launch the game.
2. Select the original retail fighter. A replacement should use the modified
   appearance directly. An extra-outfit pack should retain the original choice
   and offer another numbered outfit in that fighter's clothing selector.
3. Start a battle and check the model, movement and attacks. The Pockets example
   was tested with green pants as outfit 1 and red pants as outfit 2; the separate
   replacement pack made the original Pockets record use red pants.

For this comparison, enable only one test pack at a time. If the replacement and
extra-outfit packs are both enabled, the replacement makes the original red too.

Selector/loading portraits and titlecards are separate 2D artwork. Importing a
body atlas does not recolor them: an inherited portrait may still show the
original clothes even when the battle model is correct. Additional outfits can
use supported portrait resources; replacing retail UI artwork globally remains
outside the current replacement mode.

## Continue editing or recover from an exported pack

Use **Open project…** to reopen the saved `.ffnyfighter`, adjust its texture PNGs
and export a new ZIP filename. **Undo** reverses staged changes;
**Reset to saved** restores the saved project. Neither action uninstalls a pack.

If only the ZIP remains, extract it and choose **Import fighter from pack…**.
Select the extracted pack folder containing `fighters.json`, then the fighter
or retail override target. Save the imported content as a new `.ffnyfighter`.
Import supports an independent single-fighter pack or one appearance-only retail
override; dependencies and multi-target/global override packs are refused.
This reads the supplied pack resources rather than reconstructing an arbitrary
game archive. Keeping the original project preserves the simplest editing path.

## Shared identity and appearance ownership

An override edits the existing retail appearance without adding a roster cell.
An additional outfit preserves the original appearance and adds a hidden native
appearance record to the target's clothing choices. Both modes retain the retail
fighter's moveset, stats and voice. These controls are disabled in the studio;
use a separate fighter project for independent combat settings.

The runtime accepts at most three outfits in total for one retail target,
including its original outfits. A fighter already at that limit cannot receive
another one. The current implementation targets appearance resources and body
atlases. Replacement retail UI artwork still requires separate runtime ownership
support and is refused at export rather than silently applied globally.

## Portable contract

Existing `ffny-retail-fighter-project-1` projects keep their standalone meaning.
Version 2 adds `deployment: {mode, target}`, with `mode` equal to `add`, `override`
or `outfit`, and a stable target such as `retail/pockets`. Non-add deployments
must inherit that target and cannot override combat resources or stats.

An override exports the existing manifest `overrides` entry. An extra outfit
exports a fighter with `outfit_of` pointing to its retail parent. The matching
runtime compiles this into a hidden participant-window appearance binding and
extends the original selector's datasets. FWR2 carries the canonical retail
identity used for progress, loading and results. Existing FWR1 packs retain their
original encoding. Older runtimes do not support these new outfit bindings.

Private projects, artwork and captures are kept outside the source tree. See
PROGRESS.md for the tested workflow and qualification limits.
