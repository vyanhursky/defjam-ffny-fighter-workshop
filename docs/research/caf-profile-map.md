# CAF profile appearance map

Read-only static investigation, 2026-11-07. Addresses identify original executable
functions; no executable code, disassembly, save contents or extracted assets are
included. This is implementation evidence, not native acceptance.

## Serialized arrays

Offsets below are relative to the validated 0x5904-byte profile payload. The
profile object contains that payload beginning at object+0x0C. Constructor
0x145A0 sets its appearance pointers to object+0x5564 and object+0x55FC
(0x14607..0x14619). Thus:

- Q[s] = signed little-endian dword at payload+0x5558+4*s, 38 entries.
- C[s] = unsigned byte at payload+0x55F0+s, 38 entries.

0x63780 copies exactly 0x98 and 0x26 bytes from those pointers into the preview
state, then reconstructs appearance. Q is not a uniform model/design/color tuple.
C is a per-slot option byte: clothing fitting, grooming palette, or jewelry
color ordinal depending on the builder.
The first twelve Q entries mix scalar settings and direct facial-feature choices.
Do not interpret payload+0x10 as a version.

## Slot mapping and recipe

| Slot | Meaning | Serialized recipe |
|---|---|---|
| 0 | Template/body build | Q[0] is source build index 0..5 => A..F |
| 1 | Facial/skin | Q[1] is skin palette number; positive values select plNN directly |
| 2 | ShortFace/base face | Derived by builder; Q[2] not used in this rebuild |
| 3 | Neck | Derived by builder; Q[3] not used in this rebuild |
| 4 | Face fit | Derived by builder; Q[4] not used in this rebuild |
| 5 | Head/face type | face_type = Q[5]-1 |
| 6 | Eyes | Q[6]; feature geometry and texture pattern below |
| 7 | Eye color | Q[7]; texture-only pattern below |
| 8 | Eyebrows | Q[8], palette C[8] |
| 9 | Nose | Q[9]; feature geometry and texture pattern below |
| 10 | Lips | Q[10]; feature geometry and texture pattern below |
| 11 | Ears | Q[11]; special recipe below |
| 12 | Tops | Packed clothing reference, color, C[12] fitting |
| 13 | Pants/shorts | Packed clothing reference, color, C[13] fitting |
| 14 | Shoes | Packed clothing reference, color, C[14] fitting |
| 15 | Hats | Packed clothing reference, color, C[15] fitting |
| 16 | Left wristbands | Packed clothing reference, color, C[16] fitting |
| 17 | Right wristbands | Separate packed reference; do not infer pairing |
| 18 | Hands | Packed clothing reference, color, C[18] fitting |
| 19 | Eyewear | Packed clothing reference, color, C[19] fitting |
| 20 | Hair | SODB hair-table row, C[20] palette |
| 21 | Facial hair | SODB hair-table row, C[21] palette |
| 22 | Necklaces | SODB jewelry row, C[22] color ordinal |
| 23 | Bracelets | SODB jewelry row, C[23] color ordinal |
| 24 | Watches | SODB jewelry row, C[24] color ordinal |
| 25 | Left earrings | SODB jewelry row, C[25] color ordinal |
| 26 | Right earrings | SODB jewelry row, C[26] color ordinal |
| 27 | Teeth | Direct integer, special recipe below |
| 28 | Rings | SODB jewelry row, C[28] color ordinal |
| 29..37 | Tattoos | SODB tattoo row; independent placement from slot index |

Tattoo slots in order: head/neck, chest/stomach, back, left arm, left forearm,
right arm, right forearm, left leg, right leg. Q=-1 means no selected database
item. C=255 occurs for empty tattoo slots; tattoo builder does not use C.
Preserve opaque Q[2..4]; their user-facing meanings were not established here.

## Database reference and clothing join

For database-backed slots, decode unsigned U=Q[s]:

- table_index = U >> 24 (ordinal in sorted SODB DATA mapping).
- color = (U >> 16) & 255, for clothing.
- fitting = C[s], for clothing.
- row_ordinal = U & 65535.
- record_ref = U & 0xFF00FFFF.

0xBE760 resolves table_index and row ordinal; its callers clear the embedded color byte
before lookup. This is a positional record reference, NOT the hash key exposed
as caf_shop clothing id. For this source, table index 16 is clothing
(hash 0x912016DD), 14 is hair (0x7450591A), 5 is jewelry (0x426B8667),
and 4 is tattoos (0x30948EA0). Validate the source table hashes rather than
assuming ordinals across different source revisions.

The row ordinal selects insertion order of the primary-index mapping, whose
values are record offsets. Preserve that order before any sorting for UI display.
Convert it to the primary hash key used by the existing wardrobe catalogue.
Then its embedded color ordinal and fitting C[s] select the existing
colors[].fittings[].selection XML triple. Do not use the low16 value as its id.
0x62EC0 and 0x1FE70 establish this route.

Clothing geometry is base model plus fitting-offset; texture is design and the
color record's resource number. Existing caf_shop wardrobe() implements the
source aliases for headwear, shorts and taped fingers. Keep those joins.
Q=-1 selects original fallback body geometry for slots12/13/14/18, and no part
for most accessory slots; empty is not always equivalent to no geometry.

## Direct face components

0x62BA0: Eye Q[6]=1 disables the extra eye feature. Otherwise geometry
V2CP_541_000N_C and texture V2CP_541_000N_A01_01, with N=Q[6].
0x62C10: Eye color is NON_GEOM plus V2CP_542_000N_A01_01, N=Q[7].
0x62C60: Brow is NON_GEOM plus V2CP_551_000N_A01_01, N=Q[8], palette C[8].
0x62CB0: Nose Q[9]=1 disables extra feature; otherwise
V2CP_561_000N_C and V2CP_561_000N_A01_01.
0x62D20: Lips Q[10]=1 disables extra feature; otherwise
V2CP_571_000N_C and V2CP_571_000N_A01_01.
0x62D90: Ears Q[11]=1 disables extra feature. Remap value 4 to2; geometry
V2CP_581_000N_C. Odd N has V2CP_581_000N_A01_01; even N has no ear texture.
These are literal game filename formats; do not zero-pad the trailing N beyond
what the template states.

The feature geometry is morph data targeting the base face, not independent
opaque meshes. 0x9B220 copies selected eyes/nose/lips/ears geometry into each
slot's morph name; 0x9A910 applies slots 4/6/9/10/11 to target slot 2.
Initialization 0x994C0 gives weight 1; setter 0x26140 clamps it to float bits
0x3F7FF972 (approximately 0.9999). Preserve source render-mesh identity when
adding coordinate deltas. Full-face decode needs the base mesh and all selected
morph resources; rendering these morphs as separate meshes is incorrect.

## Whole face reconstruction omitted by default viewer

0x98820 consumes build b=Q[0] and t=Q[5]-1:

- Slot0 template: odd t => V2CP_Template_Norm, even t => V2CP_Template_Long.
- Slot1 facial resource: odd t => V2CP_532_0002_C_F;
  even t => V2CP_532_0001_C_F.
- Slot2 base mesh: V2CP_532_0004_C.
- Slot3 full neck: V2CP_530_0001_[A-F], using b directly.
- Slot5 scalp: V2CP_210_0001_C for t<4, suffix C1 for t>=4.
- Slot4 face-fit morph: V2CP_53G_000F_C, G=b//2+1, F=t%4+1.
  Exception: b//2==1 and t in {3,7} => NORMAL, so no face-fit morph.

Thus the previous fixed type 0 face fit only covers one of four fit shapes and
one template/scalp family. Apply slot4 and the chosen eye/nose/lip/ear morphs
to slot 2 using original mesh identities. Facial and feature textures, skin and
brow palettes must follow the choices above. 0x9AB90 loops all 38 slots and
runs geometry then morph construction. Retaining all raw objects in the private
cache allows this additional face decoding without shipping game-derived data.

Facial-hair full-model fit 0x98D40 additionally uses body mapping A/A/C/C/F/F
and face suffix t%4+1 for values 1..3; value 4 leaves the build letter
unsuffixed. Hair/headwear attachment changes remain a compatibility issue;
0x98A90 and 0x98C40 adjust them according to the selected hat/hair and scalp.

## Hair, jewelry, tattoos and teeth

Hair 0x63070 and facial-hair 0x631B0 resolve the Q database row. In this source,
hair record word 3 is model-string index (schema field 0xC38D6E96), word 7 is
texture-string index (field 0x80675C36). Texture substring[9:13]==0001 means
no selected hair. If model character[9] is9, omit geometry; otherwise append
_C to the model stem. Use C[s] as palette ordinal (pl(C+1)), not an XML texture
color ordinal. Facial-hair model is then remapped by 0x98D40 as described above.

Jewelry 0x632F0, also expanded in 0x63780: top record word 1 is resource stem
(e.g. part/model/design without V2CP prefix or color). Word3 points to the
count+pointer color-array; C[s] selects a nested record. Nested word 3 is the
texture resource color number. Resource name = V2CP_<stem>_<color:02d>.
Geometry takes the first 14 characters of that full resource and appends C
(the standard V2CP_part_model_C stem). The source
applies a special 143->142 taped-finger alias and corresponding model-digit
adjustments; existing XML authoritative matching must retain those aliases.
Nested word 1 is additionally passed to the part setter when <=3 (otherwise-1);
its rendering/compatibility semantics remain unproven here. The nested schema
field is0x55E507D3. Earring reconstruction is paired: after building slot 25,
0x63780/0x632F0 also builds slot 26 from the selected left item. For part341,
model final digit 1 or4 is increased by 4. For part342/343, the two-digit model
number is increased by 11. These changes apply to model and texture names. Other
earring parts reuse their names. Q[26] is not independently consumed during
0x63780 full reconstruction, even though the general update dispatcher can
address 26. Do not infer independent saved right-ear geometry from Q[26].

Tattoo 0x63560: top record word 2 is a zero-based design/category digit
(field 0x7C88C033), word 3 is the model number (field 0xD1F27DB6). For slot s,
resource = V2CP_4< s-28 >< word 2+1 >_< word 3:04d >_A01_01.
Geometry is NON_GEOM. C[s] is ignored by this builder.

Teeth 0x62E40: Q[27]==-1 uses NON_GEOM and V2CP_354_0001_A01_01.
Otherwise texture = V2CP_35< Q//7+1 >_000< Q%7+1 >_A01_01,
with C[27] passed to the part setter. The texture compositor palette dispatch
does not include slot 27, so palette behavior for teeth is not established; do not
apply a palette merely because that byte exists. Do not resolve teeth as a SODB reference.

## Verification and limits

All four existing profiles were read through the standalone validated container
reader; no saves were written. Their populated scalar/feature arrays and packed
clothing/hair/jewelry/tattoo references fit this layout. The observed first two
wardrobe defaults resolve through primary-index ordinals to pants and shoes,
providing a useful cross-check of positional indexing. Original files remain
untouched by this investigation. No game, build or viewer was started.

This establishes loading recipes, not valid editing ranges, retail body-size
labels, every jewelry compatibility rule, native morph acceptance or animated
attachment correctness. Unknown bytes must be preserved. Feature type and
palette bounds should come from the owner's accepted source resources.

Palette dispatch was checked directly: in 0x9A050, slots6/9/10/11 use the skin
palette Q[1]; slot8 uses C[8]+1; slot 20 uses C[20]+1; slot 21 uses C[21]+1.
The palette prefix is pl in each case. Slots7/12..19 and27 do not take these
palette branches. Skin zero bypasses the alternate palette. Face morph target
switch 0x9A910 explicitly maps4/6/9/10/11 to mesh slot 2.

Clothing option-byte correction verified against 0x1FE70 parameter use: its first
array query is fitting field 0x7C853FA8, indexed by C[s]. Its second is color
field 0xAC3E66A4, indexed by the packed reference byte at bits16..23. The two
must not be interchanged. Cross-save option counts reject the swapped recipe.

## Additional bounded checks

Core empty clothing choices in 0x62EC0 are exact:

| Slot | Geometry when Q=-1 | Texture |
|---|---|---|
| 12 | V2CP_110_0001_C | none |
| 13 | V2CP_120_0001_C | V2CP_120_0001_A01_01 |
| 14 | V2CP_130_0001_C | none |
| 18 | V2CP_140_0001_C | none |
| 15/16/17/19 | none | none |

The paired-earring rule has a source inconsistency worth preserving as unknown:
0x634FB and 0x63F3E both compare part341's model final digit to exactly1 OR4,
not the inclusive interval1..4. Thus341_0001 becomes341_0005 and341_0004
becomes341_0008, but341_0002/0003 are reused by that code. The right XML group
nevertheless contains341_0006/0007. Likewise344_0001 is reused even though the
right XML group lists344_0002. Do not broaden the rule and claim that behavior
is proven. Left-only rendering with an explicit unresolved pairing, or an
explicitly inferred XML-counterpart preview, is more honest pending native checks.
The part342/343 rule adds11 to the two-digit model field, e.g.342_0001 to342_0012.

The group1 C_F resources are NOT textures or visible mesh objects. Both contain
a PosePaletteBank export, with no model or morph export. 0x999D0 loads the
selected object. 0x980B0's slot1 switch branch at0x9812E passes its bytes to
0x215E0 and stores the PosePaletteBank at CAF+0x9E00. Mesh mounting in0x9AB90
starts at slot2. The expression path0x17EBE passes that bank to0x17A40, which
attaches pose data to animation nodes using the model skeleton pose, then
0x9C0A0 refreshes posed geometry. No static rest-pose modification by this bank
was observed in the bounded reconstruction path. Preserve its selected identity
for future animation support; do not treat it as an XSH skin-palette map. Skin
adaptation for a neutral static preview is the four base atlas palettes and the
selected direct component palettes already described. No per-part palette is
applied to slots1/2/3/5 in the compositor route.
