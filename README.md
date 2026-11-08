# Def Jam FFNY Fighter Workshop

A standalone, offline desktop Create-a-Fighter and save editor for **Def Jam:
Fight for NY Recomp**, targeting Windows, macOS and Linux.

**Development preview — `develop/0.1`.** Windows functional checks pass; full owner
acceptance and native macOS/Linux validation are pending. This repository
currently publishes source; no packaged release is available yet.

Local beta: browse existing profiles, preview the saved fighter in 3D, edit
appearance, training stats, cash, development points and retail CAF style
combinations. Save with an original-profile backup, export/import a complete
profile, or duplicate it under a new ID while retaining Story progress.

Items, colors and fits preview immediately as you browse. **Equip** adds the
choice to Pending Changes; **Save changes** writes the profile. Tattoo categories
are grouped and named by body area. **No clothes** temporarily hides apparel and
accessories, retaining underwear, so tattoos are easier to inspect.

The viewer offers Wardrobe-inspired, Relaxed and source T-pose, plus Studio,
Warm shop, Cool rim and Texture reference lighting. Wardrobe-inspired and Relaxed
use approximate preview deformation, not the retail shop animation. Uncommitted
try-ons are excluded from saves and exports. Equip stages an item; clothing
visibility, pose and lighting always remain preview-only.

Keep the complete application folder together and launch the Windows executable.
Choose **Open data directory** and select the Recomp directory containing `save`
and `extracted`. Start with separate copies of your saves and close the game using
those copies before editing. Original game assets are decoded locally; nothing
is uploaded or downloaded at runtime.

**Export** includes staged changes and the complete profile. **Duplicate** creates
a separate profile with staged changes and a new 1–7 character uppercase/digit
ID. **Import** installs into the selected directory and refuses name collisions.
**Save profile** changes the selected profile after creating a `.djprofile` backup
in the editor workspace's `backups` directory.

See [the test guide](docs/beta-test-guide.md) and [validation](docs/validation.md).

```sh
python -m pip install -e '.[desktop,dev,build]'
defjam-caf-desktop --data /path/to/recomp-data
defjam-caf inspect --data /path/to/recomp-data
python -m pytest -q
node --test tests/poses.test.mjs
python scripts/package_desktop.py
```

Point at the Recomp data directory containing `save` and `extracted`. The inspector
also accepts a `save`, `UserData`, or title-save directory. Inspection never writes
to the selected data directory. It distinguishes global Options from profiles,
preserves legacy folder identities and reports ambiguous or invalid entries.

See [the agreed scope](docs/specification.md), [format evidence](docs/save-format.md)
and [development status](PROGRESS.md). Game assets and saves are not distributed.
Preview assets are derived locally from the user's own game files. Initial
conversion takes several minutes; later launches reuse a private cache.

Builds use PyInstaller and include their own Python runtime; the target machine
does not require Python. Build on each target OS. macOS/Linux require native
package validation.
`requirements-tested.txt` records the local Windows build environment.

If a restricted Windows build workspace labels generated files Low integrity,
Qt's sandboxed renderer cannot start. In a normal PowerShell session, restore
only the generated app folder to the ordinary Medium level, then verify the
packaged preview:

```powershell
icacls 'dist\defjam-ffny-fighter-workshop' /setintegritylevel '(OI)(CI)M' /T /Q
```

This does not disable Chromium sandboxing or change Windows security policy.
