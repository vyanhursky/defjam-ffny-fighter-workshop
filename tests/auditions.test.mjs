import { test } from "node:test";
import assert from "node:assert/strict";
import { createAuditions, voiceRequests } from "../src/defjam_caf/resources/auditions.mjs";

test("auditions share pending work, normalize keys, evict bounded data and isolate contexts", async () => {
  const requests = [];
  let finish;
  const cache = createAuditions({
    maxBytes: 8,
    load: async (request) => {
      requests.push(request);
      if (requests.length === 1)
        await new Promise((resolve) => {
          finish = resolve;
        });
      return { mime: "audio/wav", data: "aaaa" };
    },
  });
  cache.context("first");
  const first = cache.get({ voice: 1, index: 0 }),
    same = cache.get({ index: 0, voice: 1 });
  finish();
  await Promise.all([first, same]);
  assert.equal(requests.length, 1);
  await cache.get({ index: 0, voice: 1 });
  assert.equal(requests.length, 1);
  await cache.get({ voice: 1, index: 1 });
  await cache.get({ voice: 1, index: 0 });
  assert.equal(requests.length, 3);
  cache.context("second");
  await cache.get({ voice: 1, index: 0 });
  assert.equal(requests.length, 4);
});

test("a context change stops obsolete preparation and failed clips do not stop the batch", async () => {
  const calls = [],
    progress = [];
  let finish;
  const cache = createAuditions({
    load: async (request) => {
      calls.push(request);
      if (request.wait)
        await new Promise((resolve) => {
          finish = resolve;
        });
      if (request.fail) throw Error("unsupported codec");
      return { data: "aaaa" };
    },
    progress: (value) => progress.push(value),
  });
  const old = cache.prepare([{ wait: true }, { obsolete: true }]);
  cache.context("new");
  finish();
  await old;
  assert.equal(calls.length, 1);
  await cache.prepare([{ fail: true }, { valid: true }]);
  assert.deepEqual(progress.at(-1), { done: 2, failed: 1, total: 2 });
});

test("preparation covers every selected bank and all entrance/victory streams", () => {
  const requests = voiceRequests(
    { voice: 3, streams: { intro: ["intro-a", "intro-b"], extro: ["victory"] } },
    { Taunts: 8 },
    [
      { category: "Character", voice: 3, count: 2 },
      { category: "Taunts", voice: 8, count: 1 },
    ],
  );
  assert.equal(requests.length, 6);
  assert.deepEqual(requests[2], { category: "Taunts", voice: 8, index: 0 });
  assert.deepEqual(requests.slice(3), [{ stream: "intro-a" }, { stream: "intro-b" }, { stream: "victory" }]);
});
