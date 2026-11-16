# Synthetic Qt workflow checks

`scripts/synthetic_ui_smoke.py` drives the real pages, Qt/WebChannel, editor
requests, profile transactions/backups, project persistence and WebGL. It creates
invented data only. It adapts original-resource/compiler responses and native
picker/confirmation answers; it cannot qualify original assets or gameplay.

```sh
python scripts/synthetic_ui_smoke.py --output build/ui-tour-wide --size 1440x940
python scripts/synthetic_ui_smoke.py --output build/ui-tour-compact --size 1100x760
```

The output directory must not already exist. Text receipts record every completed
step, request counts and limits. `--capture` keeps local screenshots for inspection;
CI uploads receipts only. The synthetic workflow runs on affected PRs and nightly
under Xvfb/software WebGL. Original-asset `desktop_smoke.py` and the focused
authoring smoke scripts remain separate private, disposable-data checks.

The tour checks Home, a Story edit/backup and unchanged unknown bytes, project
creation, project/outfit sidebar, mirrored outfit selection, keyboard tabs,
automatic catalog failure/retry from Entrance, AI reuse, named UI donors, pinned
changes and export preflight/save before a cancelled ZIP chooser. It asserts
that the nonvisual stat edit does not request another preview. A compiler and
native game acceptance require the actual compatible game and independent data.

## Retail coverage

The same tour also starts a standalone retail fighter, synchronizes its starting
donor choices, imports an invented body through a boundary adapter and observes
automatic WebGL preview/texture shapes. It checks keyboard tabs, readable IDs,
collapsed setup and both replacement and extra-outfit modes with shared combat
controls disabled. These checks validate workflow behavior, not retail compilation.
