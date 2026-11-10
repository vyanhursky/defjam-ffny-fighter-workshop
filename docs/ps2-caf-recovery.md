# Experimental PS2 CAF recovery

This recovers fighter fields from the intact EE-memory image in a PCSX2 `.p2s`
snapshot, optionally inside a texture-mod ZIP. It does not import memory cards,
convert Story profiles, execute emulator state, or install texture replacements.

```sh
python -m pip install -e '.[ps2]'
defjam-caf inspect-ps2-caf example.p2s --name DEMO
defjam-caf import-ps2-caf mod.zip --name DEMO --data /path/to/recomp-data \
  --donor retail/blaze --out demo.ffnyfighter
```

Use the exact uppercase profile name. Inspection reads the archive without
extracting files. Import requires the Xbox dump and maps equipped SODB items by
table and record identity, even when platform row ordinals differ. It writes a
new standalone project through the normal collision-safe project writer. It
does not write the source archive, source profile or selected game data.

The observed PS2 layout keeps the five training stats at profile+`0xf0`, retail
styles and their combined core at `0x134`, and the 38 appearance dwords at
`0x5560`, followed by 38 color bytes. The Xbox profile's appearance begins at
`0x5558`: copying a PS2 profile wholesale would read the wrong fields. Unknown
bytes, career/currency, inventory and console ownership are excluded. Body
indices retain the verified A–F resource mapping; no retail weight label is
inferred from that letter.

The reader bounds archive/member sizes and Zstandard windows, checks CRC and
exact EE-memory size, requires an intact SODB, validates stat/style combinations
and item-table membership, and refuses conflicting copies or ambiguous archives
and databases. The observed PCSX2 version-record family is required. Other
versions/layouts may be refused; this is experimental recovery from an observed
snapshot, not general console/emulator compatibility.

Open the project in Workshop, then use the existing compatible-runtime export.
Native compilation is a separate check from actual game selection, combat,
save/quit, reload and appearance acceptance. Default voice/AI/presentation uses
the explicitly selected retail donor, because those are not recovered from the
CAF style combination. Imported PS2 texture filenames are emulator hashes and
must not be treated as Xbox texture identities.

The four saved retail finisher references are translated by record identity.
All four must be concrete, or all four absent; partial assignments are refused
until their original semantics are verified. No individual move is invented.

Continue with [native atlas import and fighter mod export](fighter-projects.md#native-atlas-import-and-saved-finishers-development):
versioned project assets, explicit atlas mapping, integrity checks, 3D preview,
per-fighter runtime binding and teardown, and export validation. Higher-resolution
art, individual move editing, custom meshes and animation playback remain separate work.
