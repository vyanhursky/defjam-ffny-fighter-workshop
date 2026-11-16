import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { decodeAttribute, unpackPreview } from "../src/defjam_caf/resources/geometry.mjs";

test("Python wire geometry decodes to the actual GPU float32 values without mutating metadata", () => {
  const result = spawnSync(
    process.env.PYTHON || "python",
    [fileURLToPath(new URL("./geometry_fixture.py", import.meta.url))],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 0, result.stderr);
  const wire = JSON.parse(result.stdout),
    decoded = unpackPreview(wire);
  assert.deepEqual(decoded.meshes[0].positions[0], [Math.fround(0.1), -2.5, 3.75]);
  assert.deepEqual(decoded.meshes[0].indices, [0, 1]);
  assert.equal(decoded.meshes[0].atlas, "a");
  assert.equal(wire.meshes[0].positions, undefined);
});
test("wide indices remain unsigned 32-bit and invalid buffers fail before scene construction", () => {
  const data = Buffer.alloc(4);
  data.writeUInt32LE(65536);
  const decoded = decodeAttribute({ kind: "u32le", count: 1, components: 1, data: data.toString("base64") });
  assert.equal(decoded[0], 65536);
  assert.ok(decoded instanceof Uint32Array);
  assert.throws(() => decodeAttribute({ kind: "f32le", count: 10, components: 3, data: "" }), /Invalid/);
  assert.throws(() => decodeAttribute({ kind: "f32le", count: 3, components: 3, data: "" }), /Truncated/);
});
