import { test } from "node:test";
import assert from "node:assert/strict";
import { projectLocation } from "../src/defjam_caf/resources/project-workflow.mjs";
import { nextTabIndex } from "../src/defjam_caf/resources/tabs.mjs";

test("project panel splits native paths while retaining the filename", () => {
  assert.deepEqual(projectLocation("C:\\Fighters\\Example.ffnyfighter"), {
    name: "Example.ffnyfighter",
    folder: "C:\\Fighters",
  });
  assert.deepEqual(projectLocation("/fighters/Example.ffnyfighter"), {
    name: "Example.ffnyfighter",
    folder: "/fighters",
  });
  assert.equal(projectLocation(null).name, "Unsaved project");
});
test("arrows wrap, with Home and End shortcuts", () => {
  assert.equal(nextTabIndex(0, "ArrowUp", 9), 8);
  assert.equal(nextTabIndex(8, "ArrowDown", 9), 0);
  assert.equal(nextTabIndex(4, "Home", 9), 0);
  assert.equal(nextTabIndex(4, "End", 9), 8);
});
