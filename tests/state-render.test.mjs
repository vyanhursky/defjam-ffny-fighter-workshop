import { test } from "node:test";
import assert from "node:assert/strict";
import { shouldRefreshAppearance } from "../src/defjam_caf/resources/state-render.mjs";

test("nonvisual changes keep the preview; appearance and explicit refreshes rebuild it", () => {
  const original = { appearance_key: "same", fields: { cash: 1 } };
  assert.equal(shouldRefreshAppearance(null, original), true);
  assert.equal(shouldRefreshAppearance(original, { ...original, fields: { cash: 200 } }), false);
  assert.equal(shouldRefreshAppearance(original, { ...original, appearance_key: "new" }), true);
  assert.equal(shouldRefreshAppearance(original, original, true), true);
});
