import { test } from "node:test";
import assert from "node:assert/strict";
import { workshopVersion } from "../src/defjam_caf/resources/version.mjs";

test("consistent friendly release labels retain meaningful patch numbers", () => {
  assert.equal(workshopVersion("0.1.0b2"), "Fighter Workshop 0.1 beta 2");
  assert.equal(workshopVersion("0.1.1"), "Fighter Workshop 0.1.1");
});
