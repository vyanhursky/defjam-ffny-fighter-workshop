# Recomp profile container: evidence and open work

2026-11-07. This describes observations from the owner's local Xbox-based Recomp
saves, not general console-save support. No save bytes are included here.

## Container

Little-endian header, 76 bytes:

| Offset | Size | Meaning |
| --- | --- | --- |
| 0x00 | 4 | Integer 0x4d433032 (on-disk ASCII `20CM`) |
| 0x04 | 4 | Total file length |
| 0x08 | 4 | Chunk 0 length |
| 0x0c | 4 | Chunk 1 length |
| 0x10 | 20 | HMAC-SHA1 of chunk 0 |
| 0x24 | 20 | HMAC-SHA1 of chunk 1 |
| 0x38 | 20 | HMAC-SHA1 of bytes [0, 0x38) |
| 0x4c | chunk 0 length | Identifier metadata |
| following | chunk 1 length | Profile or Options payload |

The inspected Recomp saves match all three HMACs with a 16-byte zero key.
The runtime's kernel bridge initializes XboxSignatureKey to 16 zero bytes.
This is a Recomp compatibility parameter, not a key extracted from a console.
Plain SHA1 does not match. Reject other signatures rather than silently resigning
an unsupported save.

The observed character payload length is 0x5904 (22,788); chunk 0 is 64 bytes;
total length is 22,928. Options has a different payload length and is not a CAF.
Payload begins with a 16-byte NUL-terminated ASCII profile name. A following
32-bit word differs between valid profiles (observed 1 and 4); its meaning is
unverified and it must not be treated as a format version. Other fields remain
opaque until established.

The retail constructor at 0x000148b0 clears a 0x5904 region at object+0x0c.
The container constructor at 0x001978ac writes the MC02 magic. These observations
support the layout but do not independently prove every payload field.

## Discovery and names

Recomp uses `save/UserData/45410049/<directory>/SaveMeta.xbx`; metadata is UTF-16
with a `Name=` record. The profile file uses that name. A folder can contain a
stale second payload, so never select the first non-metadata file.

Canonical directory names are 12 uppercase hex digits from the polynomial hash
over UTF-16 code units modulo 2^48-59. The Recomp also accepts a precise legacy
last-nibble variant only after exact name/metadata matching and when the
canonical folder does not exist. Source: Recomp `src/hooks/save_compat.c`.

## Editable fields and acceptance

Mapped fields, retail selection encodings, style bonuses and assembly rules are
documented in `research/profile-fields.md`, `research/caf-profile-map.md` and
`research/caf-wrist-hair-compatibility.md`. Inventory ownership is separate from
equipped selections and is preserved. Unverified bytes remain opaque.
`validation.md` records native load, normal re-save and fresh-process reload of
an edited, transferred and duplicated profile.
