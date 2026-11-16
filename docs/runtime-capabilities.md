# Discovering game capabilities

Workshop reads game capabilities without executing the selected runtime. New
runtime sources can provide `scripts/fighter-contract.json`:

```json
{"api": 1, "commands": ["catalog", "validate"], "recipe_format": "caf-fighter-1"}
```

The file is bounded to 64 KiB. API must be integer 1, commands a bounded list of
command names, and recipe_format a string. Unknown APIs, malformed JSON and
duplicate fields are refused rather than silently enabling legacy detection.
The executable contract script must still exist. When the manifest is absent,
Workshop retains its legacy source inspection for older installed game builds.

The discovery cache includes manifest timestamps/sizes and returns independent
results so scan/header labels cannot change cached capabilities. Installed build
labels retain the first eight build-hash characters; the installed release
record supplies its version when it names the same source. This distinguishes
stable and beta installations sharing a numeric version.
