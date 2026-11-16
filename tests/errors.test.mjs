import { test } from "node:test";
import assert from "node:assert/strict";
import { responseError } from "../src/defjam_caf/resources/errors.mjs";

test("player message and diagnostic detail remain separate through transport", () => {
  const error = responseError({ error: "Choose another file.", detail: "<script>private diagnostic</script>" });
  assert.equal(error.message, "Choose another file.");
  assert.equal(error.detail, "<script>private diagnostic</script>");
});
