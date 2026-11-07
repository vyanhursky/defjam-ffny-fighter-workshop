# Local beta test guide

1. Open the desktop application with a separate copy of your Recomp data. A copy
   of `save` plus access to the original `extracted` directory is sufficient.
2. Select an existing Story fighter. Rotate with the mouse, zoom, and use the
   front/back buttons. Compare the body, face, clothing, hair and tattoos with
   the game. The pose is static and the lighting is approximate.
3. Change body build or skin, then select a clothing/hair/tattoo category and
   choose a retail item, color and fitting. Click Equip. Check that the preview
   and pending change list update. Undo reverses the last staged action; Reset
   discards all staged edits.
4. In Stats & cash, edit the five training stats (0–50), cash (0–10,000,000), and
   development points (0–100,000). These currency limits are conservative beta
   policies verified by game load/save, not claimed universal format maxima.
5. In Fighting styles, choose one to three distinct retail styles and apply.
   The editor updates the dependent combination and style bonuses, preserving
   other earned bonuses. Named-fighter movesets are deferred.
6. Export the edited profile. Duplicate to a new ID. Confirm both preserve Story
   progress and that the original profile remains selected only when intended.
7. Save an edit to the duplicate, review the confirmation and check that a
   `.djprofile` backup appears in the editor workspace's `backups` folder.
8. Open a second disposable Recomp data directory, then import the export.
   Reopen the imported profile and compare the saved fields and appearance.
9. Launch the game against that disposable directory. Load Story, inspect the
   fighter and wardrobe, then save normally, quit, reopen and compare again.

Report the profile ID, action/item selection, expected result and observed
result. The workspace `logs/desktop.log` records packaged startup errors. Keep
saves and extracted assets private when filing public issues.

## Known beta limits

Existing Xbox-based Recomp profiles only. Profiles without a Story fighter are
read-only until the game creates one. Full-profile transfers include progress;
there is no fighter-only preset format yet. Import and duplication refuse
collisions instead of replacing an existing profile.

The preview is a static CAF assembly, including saved face morphs, rather than
the game's full animation/expression/shader system. Some hat/hair combinations
are fitted or hidden using verified retail rules. Unknown appearance encodings
are preserved. XML-only right-wrist models have no established retail-save
encoding and are not exposed as writable options. Existing paired earrings are
resolved by the retail pairing rules. New face sculpting is deferred.

Windows is the local test target. macOS and Linux packaging and native acceptance
remain to be performed. Custom content and granular movesets remain on the
roadmap in the specification.
