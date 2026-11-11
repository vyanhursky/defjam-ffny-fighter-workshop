# HD CAF atlases

In a standalone CAF project, choose an outfit under Project, select A/B/C/D/D1/D2
and import a complete square 256, 512, 1024 or 2048px PNG. Keep the original atlas
UV layout; increasing resolution does not move body or clothing regions.
Imported PNG bytes remain intact through save, reopen and ZIP export. The
preview retains the full RGB resolution and scales the original material alpha
with nearest sampling. PNG alpha is not interpreted as a new clothing or skin
material. The preview shows D; D1/D2 are injury variants used in-game.

Changing garments changes their UV coverage. Build the new garment's source
atlas before painting it; an old tank-top atlas is not a long-sleeved hoodie
texture. Clear imported atlases to inspect the original garment layout.

HD exports declare `caf-fighter-7` and require the matching runtime and its
published toolkit pin. Export validation rejects older runtimes. A 256px-only
project retains its existing CAF export capability. Original projects and Story
profile workflows remain supported.

The runtime keeps a native 256px RGB fallback and uses the existing HD texture
loader, independent-channel mips, GPU uploader and cache budget for full-detail
rendering. It preserves the native material alpha for each live outfit and
injury atlas. No game memory limit is increased. PNG imports are limited to
16 MiB each; portable projects to 384 MiB; the deduplicated compiled HD atlas
companion to 128 MiB. 1024px is a practical starting point for a multi-outfit
fighter. Native visual/performance acceptance is separate from editor and
compiler verification. Artwork and private authoring workspaces are never
included in the Workshop source.
