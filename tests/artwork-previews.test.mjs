import test from "node:test";
import assert from "node:assert/strict";
import { artworkPreview } from "../src/defjam_caf/resources/artwork-previews.mjs";

const references = {
  images: { selector_2p: "original-selector", grid_normal_3p: "original-grid", result_2p: "original-icon" },
  layouts: { selector_2p: [256, 512], grid_normal_3p: [32, 32], result_2p: [64, 64] },
};
test("references show exact roles and labelled representatives without creating overrides", () => {
  const imports = {};
  assert.equal(artworkPreview(imports, null, "selector"), null);
  const preview = artworkPreview(imports, references, "selector");
  assert.equal(preview.png, "original-selector");
  assert.match(preview.caption, /2-player example/);
  assert.equal(artworkPreview(imports, references, "grid_normal_3p").png, "original-grid");
  assert.deepEqual(imports, {});
});
test("imported master/variant previews can be compared with the original donor", () => {
  const imports = { selector: "master", selector_2p: "specific", icon: "icon" };
  assert.equal(artworkPreview(imports, references, "selector_2p").png, "data:image/png;base64,specific");
  assert.equal(artworkPreview(imports, references, "selector_3p").png, "data:image/png;base64,master");
  assert.equal(artworkPreview(imports, references, "grid_normal_3p").png, "data:image/png;base64,icon");
  assert.equal(artworkPreview(imports, references, "selector_2p", true).png, "original-selector");
  assert.equal(artworkPreview({}, references, "loading_4p"), null);
});
