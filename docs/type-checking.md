# Checked internal document contracts

Install the dev extra and run `python -m mypy`. CI runs the pinned checker on
every native platform. `contracts.py` describes admitted fighter/retail projects,
outfits, textures, UI art, face sculpts, performance settings and editor snapshots.
They are ordinary dictionaries at runtime; no project or recipe format changes.

Outfits and contracts use all strict checks. Project functions have typed
arguments/returns and checked bodies, with calls into existing untyped codec and
catalog helpers allowed. JSON admission alone accepts `Any`; the validator casts
to the document union only after existing validation succeeds. Overloads preserve
the known CAF/retail type of an already typed document. Do not cast raw JSON in
callers to bypass admission.

The editor adoption boundary is `Editor.project` and `snapshot()`; its annotated
body is checked for unknown snapshot keys and incompatible values. Other editor
handlers and imported legacy decoders are still outside strict checking. This is
an explicit incremental adoption of B6, not a claim that the entire editor is
strict. Extend annotations and narrow the module exceptions as handlers migrate;
keep new contract/outfit code strict and avoid blanket ignores. Optional asset
copies use explicit keys so each asset retains its own value type.

Malformed input is still refused by runtime validators and covered by pytest.
Static checks cannot prove file integrity, game compatibility or unknown-byte
preservation; those retain their existing independent tests.
