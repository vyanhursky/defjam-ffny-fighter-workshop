import { test } from "node:test";
import assert from "node:assert/strict";
import { createBridge } from "../src/defjam_caf/resources/bridge.mjs";

function signal() {
  let receiver;
  return {
    connect(fn) {
      receiver = fn;
    },
    emit(value) {
      receiver?.(value);
    },
  };
}
function endpoint() {
  const sent = [],
    response = signal(),
    progress = signal();
  return {
    sent,
    response,
    progress,
    dispatch(raw) {
      sent.push(JSON.parse(raw));
    },
  };
}
test("out-of-order responses preserve identity, errors, details and busy counts", async () => {
  const changes = [],
    client = createBridge({ onBusy: (count) => changes.push(count) }),
    host = endpoint();
  client.connect(host);
  const a = client.call("first", {}, "Saving"),
    b = client.call("second", {}, "Updating");
  host.response.emit(JSON.stringify({ id: host.sent[1].id, result: 2 }));
  host.response.emit(JSON.stringify({ id: host.sent[0].id, error: "Try again", detail: "Precise diagnostic" }));
  assert.equal(await b, 2);
  await assert.rejects(a, (error) => error.message === "Try again" && error.detail === "Precise diagnostic");
  assert.deepEqual(changes, [1, 2, 1, 0]);
  assert.equal(client.pending.size, 0);
});
test("queued actions are never dropped and continue after a rejected action", async () => {
  const client = createBridge(),
    host = endpoint();
  client.connect(host);
  const first = client.enqueue(() => client.call("save"));
  const second = client.enqueue(() => client.call("export"));
  await Promise.resolve();
  assert.equal(host.sent.length, 1);
  host.response.emit(JSON.stringify({ id: host.sent[0].id, error: "Invalid draft" }));
  await assert.rejects(first, /Invalid draft/);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(host.sent[1].action, "export");
  host.response.emit(JSON.stringify({ id: host.sent[1].id, result: true }));
  assert.equal(await second, true);
});
test("dispatch failure releases busy state and messages stay bounded", async () => {
  const counts = [],
    client = createBridge({ onBusy: (count) => counts.push(count) }),
    host = endpoint();
  host.dispatch = () => {
    throw new Error("Disconnected");
  };
  client.connect(host);
  await assert.rejects(client.call("save", {}, "Saving"), /Disconnected/);
  assert.deepEqual(counts, [1, 0]);
  for (let i = 0; i < 120; i++) client.record(String(i));
  assert.equal(client.messages.length, 100);
  assert.equal(client.messages[0].message, "20");
});
