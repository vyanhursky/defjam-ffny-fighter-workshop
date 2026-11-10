# Retail appearance overrides and additional outfits

The retail studio's **Project purpose** chooses between a separate fighter,
replacement appearance for an existing retail fighter, or an additional outfit
in that fighter's original clothing selector. Choose the retail target before
importing its original appearance and a replacement texture PNG.

Save the portable `.ffnyfighter` source project, then export its mod ZIP. Import
and enable the ZIP through the game's ordinary mod installer. The source project
retains the supplied native model resources, authored PNGs and metadata for
further editing. An exported single-fighter ZIP can also be imported into the
studio. Export itself does not install or activate the pack.

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
