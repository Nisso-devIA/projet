import assert from "node:assert/strict";
import test from "node:test";
import { createStatusRetry, isServerAck, watchServerAck, watchStatusDelivery } from "../src/status-ack.js";

function emitter() {
  const listeners = new Map();
  return {
    on(name, fn) {
      listeners.set(name, fn);
    },
    off(name, fn) {
      if (listeners.get(name) === fn) listeners.delete(name);
    },
    emit(name, payload) {
      listeners.get(name)?.(payload);
    },
    size() {
      return listeners.size;
    },
  };
}

test("le statut 1 reste pending et 2 est un accusé", () => {
  assert.equal(isServerAck(1), false);
  assert.equal(isServerAck(0), false);
  assert.equal(isServerAck("PENDING"), false);
  assert.equal(isServerAck(2), true);
  assert.equal(isServerAck(479), false);
  assert.equal(isServerAck("RECEIPT"), true);
  assert.equal(isServerAck("SERVER_ACK"), true);
  assert.equal(isServerAck("READ"), true);
});

test("l'accusé arrive par messages.update puis le listener part", async () => {
  const ev = emitter();
  const pending = watchServerAck(ev, "abc", 1000);
  ev.emit("messages.update", [{ key: { id: "autre" }, update: { status: 2 } }]);
  ev.emit("messages.update", [{ key: { id: "abc" }, update: { status: 2 } }]);
  const result = await pending;
  assert.deepEqual(result, { acked: true, status: 2 });
  assert.equal(ev.size(), 0);
});

test("un ack 479 est un échec, un reçu de remise est un succès", async () => {
  const rejected = emitter();
  const pendingReject = watchStatusDelivery(rejected, "abc", 1000);
  rejected.emit("messages.update", [{ key: { id: "abc" }, update: { status: 0, messageStubParameters: ["479"] } }]);
  assert.equal((await pendingReject).status, 479);
  assert.equal((await pendingReject).acked, false);

  const delivered = emitter();
  const pendingOk = watchStatusDelivery(delivered, "abc", 1000);
  delivered.emit("message-receipt.update", [{ key: { id: "abc" }, receipt: { receiptTimestamp: 1 } }]);
  const ok = await pendingOk;
  assert.equal(ok.acked, true);
  assert.equal(ok.status, "RECEIPT");
});

test("sans accusé, l'attente se termine", async () => {
  const ev = emitter();
  const result = await watchServerAck(ev, "abc", 20);
  assert.equal(result.acked, false);
  assert.equal(ev.size(), 0);
});

test("un seul second essai est proposé", () => {
  const retry = createStatusRetry();
  assert.equal(retry.schedule("live", "titre"), "scheduled");
  assert.equal(retry.schedule("live", "titre"), "already");
  assert.deepEqual(retry.take(), { kind: "live", title: "titre" });
  assert.equal(retry.take(), null);
  assert.equal(retry.schedule("live", "titre"), "exhausted");
  assert.equal(retry.take(), null);
});
