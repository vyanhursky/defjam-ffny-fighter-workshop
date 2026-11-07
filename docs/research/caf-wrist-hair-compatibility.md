# Right wrist and static hat/hair mapping

Read-only bounded investigation, 2026-11-07. This report contains implementation
facts and original function addresses, without extracted assets, save contents,
original code or disassembly. No code was edited and no game/build/viewer was run.

## Right wrist is not a proven editable retail profile option

Group17 in the accepted CAF XML contains right-side part142 models14..23,
plus the9999 sentinel. Group16 contains the corresponding left-side numbers1..10
and the same sentinel. The obvious geometry correspondence is +13, but that
correspondence alone does not establish a serialized selection recipe.

The complete retail SODB clothing table was checked read-only: all326 rows,
all fitting offsets and all colors. Its13 armband-category rows yield70
color/fitting combinations. Every armband row has exactly one fitting with
geometry offset0. Their part142 geometry numbers are1,2,3,7,9,10. Across all
clothing categories, the taped-finger alias additionally yields142 numbers11..13.
No combination yields any part142 geometry14..23, and none yields the9999
sentinel. Thus there is no retail garment row to join to group17 using the
existing catalogue's proven model/design/color/fitting rule.

The bounded code checks support that limitation:

- 0x63780 calls the generic clothing rebuild0x62EC0 for16 and17 independently.
- 0x62EC0 does not add13 or otherwise remap slot17's resource/model number.
  It uses the selected row, packed color ordinal and C[17] fitting ordinal in
  the same way as other clothing slots.
- 0x9B220 dispatches both16 and17 through the ordinary model selection path
  0x997C0; there is no automatic left-to-right pairing branch there.
- 0x997C0's generic source build morph handling includes both16 and17, but
  source build fitting changes a selected shape, not the serialized item number.
- Q[17]=-1 has the proven empty fallback: no model and no texture.

Consequently exposing arbitrary XML right-wrist items as writable retail-save
options would require an unproven encoding. Do not invent a fitting ordinal13,
add13 to a SODB record ordinal, repurpose another table, or use an out-of-range
array value. The supported beta behavior is to preserve Q[17]/C[17] and report
unsupported selected values. XML-only viewer controls may remain separately
available as inspection controls; they are not a proven save edit. This is an
explicit source-data limitation, not evidence that the right-side models are
missing or that the raw XML renderer cannot display them.

No native right-wrist selection/re-save experiment was performed. A valid native
save selecting a right-side wrist item, or a separately identified original
caller performing the missing translation, would be the next evidence needed.

## Finite static hat/hair rules

These are geometry resource-selection rules. They do not establish pose/cloth
compatibility or animated attachment behavior. Let t=Q[5]-1 be face type.
Begin each selection rebuild with original accepted geometry names; do not
repeatedly append suffixes to already transformed names.

0x98C40 handles the fitted hat geometry in slot15. NON_GEOM and NORMAL return
unchanged. A present hat and t>=4 append the character1 to the model filename:
_C becomes_C1. The selected texture resource is unchanged.

0x98A90 handles hair geometry in slot20. When a geometric hat is present, parse
its four model-number digits at filename positions9..12. The table at0x2A4840
maps hat numbers1..38 as follows:

| Hat model numbers | Hair geometry part |
|---|---|
| 1..7,25..33 | 211 |
| 8,15..17,19..24 | 212 |
| 9..14,18,34..38 | 213 |

For a present geometric hair selection, replace the final part digit at filename
position7 with1/2/3 respectively. Keep its model number and texture selection.
Only mapped part212 additionally appends1 to the geometry filename when t>=4.
The existing hair texture resource remains from the original selected part210.
This is a full-model alternate, not a generic body shape delta.

With no geometric hat (NON_GEOM/NORMAL), a geometric hair selection keeps its
original part210 and appends1 for t>=4. If hair is NON_GEOM/NORMAL, no hair-model
remapping happens; texture-only hair can still contribute to the atlas.

An unrecognized hat model number outside1..38 returns without this hair remap;
do not index beyond the source table or fabricate a fallback mapping.

When the routine completes with geometric hair after either a valid hat-table
remap or the no-hat branch, it sets CAF runtime flag0x130 bit0. At0x9AC46,
0x9AB90's geometry-mount loop explicitly skips scalp slot5 when this bit is set.
Therefore visible geometric hair replaces the scalp, while texture-only hair
retains the scalp. Setting a new hat or hair clears this bit before recomputing
selection compatibility in0x9B220, preventing stale scalp visibility.

A source cache must retain the211/212/213 alternates and relevant_C1 objects,
even when those models do not appear as independent XML entries. Missing source
objects should produce an explicit preview limitation rather than substituted
geometry. Native acceptance of these selections remains separate.
