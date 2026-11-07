# Retail profile fields

Read-only retail-code investigation, 2026-11-07. These are original executable
virtual addresses and serialized payload offsets, not host pointers. No game run,
save mutation, or native acceptance test was performed for this report.

## Coordinate system

The constructor at `0x000148B0` clears `0x5904` bytes starting at profile object
`+0x0c` (`0x000148CA`–`0x000148DA`). Thus:

`payload offset = profile-object offset - 0x0c`.

The profile-slot accessor at `0x0001DE70` locates the object at manager
`+0x177c + slot * 0x5950`. The frontend cash and statistics readers use this same
slot layout. Container header and chunk offsets are separate from this coordinate
system; do not hard-code the commonly observed file payload start into a field
definition. The word at payload `+0x10` remains unknown and is not a version.

## Established fields

All multi-byte fields below are little-endian. Currency is read and manipulated
as unsigned 32-bit quantities; base statistics occupy 32-bit integer slots.

| Meaning | Payload | Object | Width | Evidence |
|---|---:|---:|---:|---|
| Current cash | `0x014` | `0x020` | 4 | `GetPlayerCash` handler `0x0004CA30`, read at `0x0004CA45` |
| Current development points | `0x01c` | `0x028` | 4 | `GetPlayerDevPts` handler `0x0004CA70`, read at `0x0004CA85` |
| Upper power training | `0x0f0` | `0x0fc` | 4 | Stats formatter `0x0004A360`; training write `0x0004EBCE` |
| Lower power training | `0x0f4` | `0x100` | 4 | Same six-slot array and formatter order |
| Speed training | `0x0f8` | `0x104` | 4 | Same six-slot array and formatter order |
| Toughness training | `0x0fc` | `0x108` | 4 | Same six-slot array and formatter order |
| Health training | `0x100` | `0x10c` | 4 | Same six-slot array and formatter order |
| Charisma slot | `0x104` | `0x110` | 4 | Sixth formatter value; separately recomputed by `0x00014C20` |
| Primary learned style | `0x134` | `0x140` | 1 | Learn-style handler `0x0004ED10`–`0x0004ED4A` |
| Second learned style | `0x135` | `0x141` | 1 | Same handler; presence check `0x000592FB` |
| Third learned style | `0x136` | `0x142` | 1 | Same handler; three-slot limit at `0x0004ED1B` |
| Combined combat style ID | `0x137` | `0x143` | 1 | Learn-style recomputation `0x0004ED51`–`0x0004ED8B` |
| Initial/story combat style ID | `0x4d87` | `0x4d93` | 1 | New-story setup `0x0007A3D6`–`0x0007A3F1`; distinct uses below |

The named frontend registrations are at `0x00051CA7`–`0x00051CC2`. This explicitly
distinguishes development points from neighboring point fields. The reset routine
at `0x00013AA0` independently zeroes current cash (`0x00013B8D`) and development
points (`0x00013B90`). Cash earned also updates object `+0x168`
(`0x00013610`); that historical counter is not current spendable cash.

The formatter at `0x0004A360` selects object `+0xfc` for argument `"0"`, otherwise
object `+0x114`. It labels the six values upper, lower, speed, toughness, health,
and charisma. The second array, payload `0x108` through `0x11f`, is a derived bonus
array: `0x00014C20` clears it and reconstructs it from learned-style metadata and
profile accomplishments. It is not an alternate copy of the five trained stats.
Combat conversion at `0x0001EE80` combines training and bonuses; displayed/combat
values must not be treated as the stored training value.

## Normal training range

The code supports a normal stored training range of **0–50 inclusive** for each
of the five trainable stats:

- Reset at `0x00013BFF`–`0x00013C44` clears the six training slots.
- The training handler at `0x0004EBB0`–`0x0004EBD9` increments the selected slot;
  its cost lookup uses integer `training / 5`.
- Individual achievement checks compare upper (`0x000592DF`), lower
  (`0x0005925B`), toughness (`0x00059313`), and health (`0x0005932B`) with 50.
- The all-training check at `0x00059343`–`0x00059370` requires all five,
  including speed at object `+0x104`, to equal 50.
- The completion calculation at `0x00013939`–`0x000139D6` clamps each contribution
  to 0–50 before summing toward its 250 threshold.

This establishes the normal target/cap, but the inspected increment handler does
not itself enforce the limit. It is not evidence that arbitrary out-of-range
saves are rejected. The independently derived charisma slot is not a sixth
training control and should remain preserved/recomputed by the game.

## Styles and the dependent combined ID

Each learned-style byte holds a numeric retail style `0..4`; `0xff` means absent.
The slots are ordered and contiguous. The primary style matters; exchanging only
the two secondary styles yields the same combat combination. The routine
`0x001A4700` accepts primary `0..4` and secondary arguments `-1..4`, where callers
convert an absent byte to `-1`. It obtains the combat ID through a lookup at
original address `0x002EBF6F`, indexed by `36 * primary + 6 * second + third`.

For distinct learned styles, that lookup has a compact equivalent description.
Let `a < b < c < d` be the four styles other than the primary, and assign a rank
to the secondary subset in this order:

`none, {a}, {a,b}, {a,c}, {a,d}, {b}, {b,c}, {b,d}, {c}, {c,d}, {d}`.

The zero-based lookup result is `86 + 11 * primary + rank`. The normal learn-style
path increments that result before storing object `+0x143`, so its saved value
is `87 + 11 * primary + rank`. This describes 55 combat combinations and 85
ordered distinct-style selections. It is derived semantics, not an embedded
copy of the game's lookup table. The retail metadata mapping is established below.

Two dependent bytes are important:

- New-story setup at `0x0007A3D6`–`0x0007A3F1` writes the incremented ID into both
  object `+0x143` and `+0x4d93`.
- Learning another style at `0x0004ED7F`–`0x0004ED91` updates only `+0x143` and
  then rebuilds bonuses. Combat setup reads `+0x143` at `0x00020849` and
  `0x000209D8`. The initial/story byte also acts as a presence marker at
  `0x0005F6F0`.

Therefore do not automatically mirror a style edit into the initial/story byte.
Also note that the early selection helper `0x0001E290` and direct setter
`0x0001DE40` write the unincremented supplied result to both bytes. This transient
initialization convention needs to be kept separate from the later normal saved
CAF convention. A field-only edit must update the learned-style bytes and the
combined ID together and obtain native acceptance before enabling writes.

## Currency limits and remaining uncertainty

No normal maximum cash or development-point balance was established. The cash
award function `0x00013610` and reward path at `0x00015C58` add without a visible
balance cap; spending at `0x00013640` uses an unsigned affordability comparison.
The development reward at `0x00015CC6` adds directly, and training/style purchase
deducts development points at `0x0004EDA2`.

The values 10,000,000 cash and 100,000 development points appear as conditional
grants at `0x000160C2`/`0x000160C9` and again at `0x0001613C`/`0x00016143`.
They are controlled by global flag bits and **are not evidence of currency caps**.
Neither the integer storage width nor these grants justify editable beta limits.
Verified currency limits and native save acceptance remain open.

## Follow-up: style names and metadata reader

The five rows in the owner's retail `assets/djv2.sod`, table hash `0x906455c6`,
establish the numeric mapping without inferring it from menu order:

| Saved numeric style | Retail name | Style contribution to the six bonus slots |
|---:|---|---|
| 0 | Streetfighting | Upper +2; toughness +1 |
| 1 | Kickboxing | Lower +2; speed +1 |
| 2 | Submissions | Lower +1; health +2 |
| 3 | Wrestling | Upper +1; toughness +2 |
| 4 | Martial Arts | Speed +2; health +1 |

These are derived field meanings, not a bundled asset or database dump. The
application can obtain labels and contributions from the owner's database:

1. Validate `SODB`, little-endian revision 2. Header word at file `+0x0c` points
   to `SKMA`, `+0x10` to `DATA`, and `+0x14` to `STRT`.
2. A mapping after its four-byte tag starts with count and value stride, then
   `count` 32-bit keys and `count * stride` 32-bit values. These global `DATA`
   values are file offsets. Select key `0x906455c6`.
3. Its four-word table header contains table hash, index-directory offset,
   secondary data pointer, and record count. Read the index directory as an
   untagged mapping and select its primary index under the table hash. This
   points to another mapping tagged with that same table hash; its values point
   to records. Require five records and unique numeric IDs `0..4`.
4. `SKMA` keys are table hash XOR field hash. For this table, verify field
   `0x355d7680` is record word 1 (bonus bitfield), `0xca10191c` is word 4
   (display-name string index), and `0x0e334dc7` is word 6 (numeric style ID).
   Record word 0 is the internal-name string index.
5. `STRT` starts with its tag and count, followed by `(key, offset)` pairs.
   A string index selects such a pair. Nonzero offsets point to ASCII text;
   zero offsets require the localized text under that key. All five inspected
   style display names are direct strings.

The executable confirms this interpretation: `0x00014E11` requests table
`0x906455c6`; `0x00014E68` selects the numeric ID using field `0x0e334dc7`;
`0x00014EAA` reads bonus field `0x355d7680`. The schema lookup at runtime is
the authority; the word numbers above are validated retail layout observations.

For bonus slot `j = 0..5`, the contribution of one learned style is
`(flags >> (2*j)) & 3`. The bit tests/additions implementing this are at
`0x00014ED0`–`0x00014EFA`. Sum the contribution for each present learned-style
slot, stopping at the first `0xff`, with a maximum of three slots. Retail lookup
collapses repeated styles for combat ID purposes but the bonus loop sums every
slot; preserve existing unusual saves and offer only distinct contiguous styles.

## Follow-up: load behavior and consistent bonus edits

**Raw profile loading does not automatically rebuild derived bonuses.** Load
completion at `0x000D1F70` calls `0x000156D0`. That routine constructs the object,
copies all `0x5904` serialized bytes at `0x00015726`–`0x00015731`, synchronizes
inventory counts, and returns without calling `0x00014C20`. The payload-copy
accessor at `0x000135F0` likewise copies the entire block without rebuilding it.

There are subsequent recalculation opportunities: menu lifecycle routine
`0x0005A8F0`, on its false-argument branch, calls `0x00014C20` at `0x0005AAAB`;
style learning calls it at `0x0004ED91`; equipment changes at `0x0004A320`;
post-match accomplishments at `0x00065060`. These do not prove that every existing
profile reaches recalculation before its next combat or save. A standalone edit
must keep the serialized bonus array consistent rather than depending on that.

For a style-only edit that preserves accomplishments, the minimal exact update
is, for each of the six bonus slots:

`new bonus = old bonus - sum(old learned-style contributions) + sum(new learned-style contributions)`.

Apply it to payload `0x108 + 4*j`, using metadata contributions above, together
with the new learned-style bytes and combined combat style ID. Reject an
underflow, an unsupported style, a gap, a duplicate, or a resulting inconsistent
bonus instead of guessing. This preserves accomplishment bonuses and the
separately computed charisma-training slot. It is a code-supported edit strategy;
native acceptance still needs to be demonstrated.

For an independent full bonus recomputation, first sum style contributions, then
add these accomplishment bonuses. The offsets below are **payload-relative**;
all comparisons are unsigned, and each condition contributes one unless shown:

| Bonus slot | Accomplishment conditions |
|---|---|
| Upper | u32 `+0x5c >= 100`: +1; `>= 5000`: another +1 |
| Lower | u32 `+0x60 >= 100`: +1; `>= 5000`: another +1 |
| Speed | u16 `+0x64 >= 250`: +1; u16 `+0x66 >= 250`: +1 |
| Toughness | u16 `+0x68 >= 10`: +1; u16 `+0x6a >= 25`: +1 |
| Health | u16 `+0x74 >= 5`: +1; both u32 `+0x6c >= 500` and u32 `+0x70 >= 100`: +1 |
| Charisma bonus | u32 `+0x78 >= 25`; u32 `+0x7c >= 250`; u16 `+0x80 >= 5`; u16 `+0x76 >= 5`; u8 `+0x82 != 0`: +1 each |

The original conditions occupy `0x00014F22`–`0x00015016`. This is the complete
bonus-array computation, separate from the earlier clothing/win-derived
charisma-training calculation in the same function. No accomplishment meaning
is assigned to these opaque counters by this report.

## Follow-up: signed frontend formatting and beta policy

Both current-cash and development-point frontend handlers format their 32-bit
balance through signed decimal `%d`, at original strings `0x0029482c` and
`0x00294830`. Therefore values above `2,147,483,647` can appear negative despite
unsigned balance arithmetic. The proposed beta policy ceilings of **10,000,000
cash** and **100,000 development points** avoid that signed-formatting boundary
and match explicit retail debug grants. They remain product policy ceilings,
subject to native acceptance, rather than discovered normal game maxima.

Likewise, the normal training ceiling 50 is supported by the checks documented
above, not by a discovered universal deserialization clamp. The raw six-stat
formatter uses signed `%d`; normal values `0..50` are safe in that formatting.

## Follow-up: equipped CAF items versus wardrobe ownership

**The inspected load, appearance rebuild, equipment change, and serialization
paths do not require an ownership/unlock update for a valid equipped Q/C
reference.** Equipped appearance and shop availability are separate state.
For beta's ability to equip retail items, preserve inventory state and edit only
the selected appearance references and their established dependent appearance
values. This is source evidence; durable native save/reload acceptance remains
an explicit test, especially after entering and leaving retail shops.

Evidence within the bounded paths:

- Profile loading at `0x000156D0` restores the entire serialized block, then
  synchronizes two inventory counts at `0x00015733`–`0x00015761`. It neither
  tests Q/C selections against ownership nor substitutes an owned/default item.
- Appearance rebuild `0x00063780` copies Q (`0x98` bytes) and C (`0x26` bytes)
  at `0x00063791`–`0x000637B5`. Clothing builder `0x00062EC0` resolves the selected
  Q reference directly through database resolver `0x000BE760`, then uses its
  fitting and C color in `0x0001FE70`. It has no inventory-state input or
  ownership check. Its explicit empty-reference behavior is separate from this.
- The equipment/color callback `0x0004A2A0` writes C at `0x0004A301`; for clothing
  slots it updates appearance constraints via `0x000574F0`, then recalculates
  bonuses/charisma through `0x00014C20` at `0x0004A320`. None of those operations
  reads or grants ownership. `0x000574F0` resolves the selected database item and
  metadata fitting/color; its terminal helper `0x00057260` only updates equipped
  slot masks and their aggregate.
- Full equipped-mask reconstruction `0x00015030` iterates Q/C selections,
  resolves item metadata, and passes masks to `0x00057260`; it does not filter
  through inventory availability.
- Profile save staging `0x000D23B0` copies the supplied `0x5904`-byte payload
  at `0x000D243D`–`0x000D2449`. There is no per-item ownership validation or
  normalization in that staging path.

Ownership controls the retail shop state instead: item-state formatter
`0x0004E4D7`–`0x0004E4F6` distinguishes Locked, Unlocked, and Owned through its
inventory-state flag bits. Shop-list filtering also queries the inventory
interface separately (`0x0004D07C`–`0x0004D086`). Consequently an editor-equipped
item can remain Locked or Unlocked in the retail shop until earned/purchased.
That does not invalidate its equipped appearance reference in the inspected
builder. This report does not assign editable ownership offsets because no
ownership mutation is required by the inspected equip-only workflow; it does
not authorize mass wardrobe unlocking.

Retail temporary-outfit handling is also separate from ownership: routines
`0x0004A070` and `0x0004A0B0` snapshot/restore equipped Q/C state around shop
transactions. Native durability testing should cover shop cancel/confirm as well
as a plain save/reload, without treating a deliberate transaction cancellation
as proof of an ownership requirement.

## Follow-up: retail frontend save route and resident pointer chain

To request a current-profile re-save through the original frontend, invoke
**`MemCard.Save` with one string argument: the originating SWF URL**. Registration
is at `0x0005388C`–`0x00053897`; the original handler is `0x00052B60`. This is a
retail handler invocation, not a replacement serialization implementation.

For the Story service mode (`service + 0x344 == 0`), it finds the current slot and
stages its payload at `0x00052B9F`–`0x00052BC7` through `0x000D23B0`, without a
profile dirty-bit requirement. It then enters the real memory-card save workflow
at `0x00052CD0` (`0x000D2780`). With autosave disabled, follow the displayed save
confirmation and destination prompts. Relevant original callbacks are:

| Frontend command | Argument | Handler and effect |
|---|---|---|
| `MemCard.Save` | Current SWF URL string | `0x00052B60`: stage and request save |
| `MemCard.ConfirmSaveCB` | `"0"` for affirmative | `0x00052AB0`: calls `0x000D26C0` to continue saving |
| `MemCard.ChooseSaveDstCB` | Numeric selection string, `"0"` or `"1"` | `0x00052AF0`: select destination through `0x000D29E0`, then continue saving |

`ConfirmSaveCB` interprets a nonzero response as skip/advance rather than save.
`ChooseSaveDstCB` uses values below 2 as selections; 2 or above returns to the
confirmation. Invoke these callbacks only for the corresponding live prompt;
they depend on the save workflow's staged queue/state. The actual write request
is dispatched by `0x000D20D0` to `0x000D00C0`. The Xbox device accessor
`0x000D02A0` returns a singleton device; this investigation does not assign a
portable device-name meaning to the numeric selection.

The Save URL argument also determines whether Options is staged. The exact
retail URL strings `" options/battleID.swf "`, `" options/userID.swf "`, and
`" story/Sketch.swf "` are exceptions at `0x00052C4C`–`0x00052C93`; they avoid
adding Options solely because of the originating screen. In Story mode,
`MemCard.Save(" story/Sketch.swf ")` therefore requests the current profile only,
unless independently pending Options flags cause it to be staged. Using the
actual crib URL can also include Options. Preserve spaces in these exact source
strings when intentionally selecting that route. No native save was initiated
by this report.

One save-context condition matters: the MemCard handler object's byte `+0xc0c`
is tested at `0x00052B82`. A nonzero value skips profile staging and routes to
Options staging. The normal initialized context must have this flag clear for
the current-profile path above. `MemCard.QuerySave` can affect this save-context
state. If only Options is produced, inspect the context/queue and originating
command sequence instead of assuming that a current-profile save occurred.

For read-only resident-field inspection, the frontend service registry gives a
short original-address chain. `0x00012CF0` is an indexed pointer getter, and the
cash/stat handlers select service index `0x18` from registry `0x002FB148`:

```text
service = read_u32(0x002FB1A8)
manager = read_u32(service + 0x04)
slot = read_i32(manager + 0x5ac7c)
profile_object = manager + 0x177c + slot * 0x5950
profile_payload = profile_object + 0x0c
```

Check non-null pointers, loaded registry/service state, and a valid slot before
reading. These are guest addresses and require the runtime's guest-memory
mapping; they are not host-process absolute pointers. This chain supports
comparing actual resident values to the selected serialized payload without
changing guest memory.

Rechecked against the original instructions: `0x0004A360` supplies index `0x18`
(decimal 24); `0x0004A362` places the **immediate address** `0x002FB148` in the
registry receiver, and `0x0004A367` calls the getter. `0x00012CF0` reads the
stack index and `0x00012CF4` dereferences receiver plus index times four, exactly
once. There is **no preliminary dereference of `0x002FB148`**. The next loads
are `service + 4` at `0x0004A36C` and current slot at `0x0004A36F`. The Save
handler repeats this at `0x00052B67`/`0x00052B69`/`0x00052B72`. Registration of
service 24 at `0x000126A8`–`0x000126B0`, through setter `0x00012CC0`, independently
confirms that this registry is an inline pointer array.

Read loaded service/manager addresses as unsigned 32-bit guest values. This
source establishes the pointer arithmetic, not that allocations reside in a low
guest-address range. A memory reader that scans/maps only low guest RAM can miss
the live allocation; high guest regions must use the runtime's corresponding
mapping instead of signed-address rejection or an extra guessed indirection.
