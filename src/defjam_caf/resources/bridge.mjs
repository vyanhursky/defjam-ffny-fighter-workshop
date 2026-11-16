import { responseError } from "./errors.mjs";

/** Shared request correlation, visible-operation counting, serial actions and messages. */
export function createBridge({ onBusy = () => {}, onProgress = () => {} } = {}) {
  const pending = new Map(),
    messages = [];
  let endpoint,
    serial = 0,
    visible = 0,
    tail = Promise.resolve();
  function busy(label) {
    onBusy(visible, label);
  }
  function record(message, error = false) {
    messages.push({ time: new Date(), message, error });
    if (messages.length > 100) messages.shift();
  }
  function receive(raw) {
    const message = JSON.parse(raw),
      task = pending.get(message.id);
    if (!task) return;
    pending.delete(message.id);
    if (task.label) {
      visible--;
      busy();
    }
    if (message.error) task.reject(responseError(message));
    else task.resolve(message.result);
  }
  function call(action, args = {}, label = null) {
    const id = String(++serial);
    return new Promise((resolve, reject) => {
      if (!endpoint) {
        reject(new Error("The Workshop is still opening. Try again in a moment."));
        return;
      }
      pending.set(id, { resolve, reject, label });
      if (label) {
        visible++;
        busy(label);
      }
      try {
        endpoint.dispatch(JSON.stringify({ id, action, args }));
      } catch (error) {
        pending.delete(id);
        if (label) {
          visible--;
          busy();
        }
        reject(error);
      }
    });
  }
  function enqueue(operation) {
    const task = tail.then(operation);
    tail = task.catch(() => {});
    return task;
  }
  return {
    call,
    enqueue,
    pending,
    messages,
    record,
    connect(value) {
      endpoint = value;
      endpoint.response.connect(receive);
      endpoint.progress?.connect(onProgress);
    },
  };
}
