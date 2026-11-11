# Retail fighter movesets

In **Fighting style**, choose **Retail fighter moveset**, select a fighter and
press **Apply fighting style**. Apply stages the change; Undo/Reset and Save use
the same workflow as other edits. Choose **CAF style combination** to return to
the standard primary/secondary/third style controls.

The menu reads original Character metadata from your game files. Costumes with
the same native motion core share one choice: the current Xbox database yields
69 distinct cores, including Blaze and D-Mob. This selects the original motion
core, rather than approximating it with a CAF combination. The static preview
does not play fighting animations.

Appearance, imported artwork, training and Blazin' assignments remain separate.
For projects, the retail selection is shared across all outfits. The previous
CAF style combination stays in the project for switching back. The stable
`retail_moveset` key is an optional project and recipe section; exports use the
one recipe format `caf-fighter-1`.

Direct profile editing changes the verified Battle moveset byte at payload
`0x137` only. It preserves the component CAF styles, bonuses and Story mirror
at `0x4d87`, plus all unrelated career bytes. Original game style-training
actions can recompute this byte; reapply the retail choice afterward if needed.
Creating a project from such a profile resolves and preserves its retail key.

Both direct profiles and exported fighters need the matching experimental
CAF v5 game runtime. The Beta 1 packaged game/editor do not include this work.
Native qualification evidence and remaining limits belong in `PROGRESS.md`.
