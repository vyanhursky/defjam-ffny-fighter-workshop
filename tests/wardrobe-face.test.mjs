import { test } from "node:test";
import assert from "node:assert/strict";
import { groupKey, filterOptions } from "../src/defjam_caf/resources/wardrobe.mjs";
import { faceMethodState } from "../src/defjam_caf/resources/face.mjs";

test("wardrobe groups fit variants and filters without changing original choices", () => {
  const rows = [
    { garment: "Tee", key: "12:1", label: "Blue Tee" },
    { garment: "Tee", key: "12:65537", label: "Red Tee" },
  ];
  assert.equal(groupKey(rows[0]), groupKey(rows[1]));
  assert.deepEqual(filterOptions(rows, " BLUE "), [rows[0]]);
  assert.equal(rows.length, 2);
});
test("Story and imported-sculpt face methods cannot enable unsupported controls", () => {
  assert.equal(faceMethodState({}, false, "sliders").method, "presets");
  const imported = faceMethodState({ present: true, imported: true }, true, "sliders");
  assert.equal(imported.method, "mesh");
  assert.ok(imported.locked.presets && imported.locked.sliders);
});
