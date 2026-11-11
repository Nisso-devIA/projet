import assert from "node:assert/strict";
import test from "node:test";
import {
  bareUserJid,
  chunkList,
  deliverStatus,
  refreshStatusDevices,
  statusRecipients,
} from "../src/status-send.js";

test("un numéro d'appareil et un LID ne restent pas dans la liste", () => {
  assert.equal(bareUserJid("33600000000:12@s.whatsapp.net"), "33600000000@s.whatsapp.net");
  assert.equal(bareUserJid("123@lid"), "");
  const list = statusRecipients(
    ["33600000000:12@s.whatsapp.net", "123@lid", "33611111111@s.whatsapp.net"],
    "33600000000:4@s.whatsapp.net"
  );
  assert.deepEqual(list.sort(), ["33600000000@s.whatsapp.net", "33611111111@s.whatsapp.net"]);
});

test("les appareils sont demandés par lots de 15 sans cache", async () => {
  const calls = [];
  const recipients = Array.from({ length: 16 }, (_, index) => `3360000${String(index).padStart(4, "0")}@s.whatsapp.net`);
  const result = await refreshStatusDevices(async (chunk, useCache, ignoreZero) => {
    calls.push({ size: chunk.length, useCache, ignoreZero });
    return chunk.map((jid) => ({ user: jid.split("@")[0], device: 0 }));
  }, recipients, 15);
  assert.equal(chunkList(recipients, 15).length, 2);
  assert.deepEqual(calls.map((call) => call.size), [15, 1]);
  assert.equal(calls.every((call) => call.useCache === false && call.ignoreZero === false), true);
  assert.equal(result.devices, 16);
  assert.equal(result.failedChunks, 0);
});

test("sans accusé, le second envoi garde le même id", async () => {
  const sent = [];
  let refreshes = 0;
  const result = await deliverStatus({
    createId: () => "same-id",
    refresh: async () => {
      refreshes += 1;
      return { chunks: 1, devices: 1, failedChunks: 0, deviceJids: [] };
    },
    waitAck: async () => ({ acked: false, status: null }),
    send: async (id) => {
      sent.push(id);
      return { status: 1 };
    },
  });
  assert.deepEqual(sent, ["same-id", "same-id"]);
  assert.equal(result.attempts, 2);
  assert.equal(result.acked, false);
  assert.equal(refreshes, 2);
});

test("un accusé serveur n'est pas renvoyé", async () => {
  const sent = [];
  const result = await deliverStatus({
    createId: () => "ok-id",
    refresh: async () => ({ chunks: 1, devices: 2, failedChunks: 0, deviceJids: [] }),
    waitAck: async () => ({ acked: false, status: null }),
    send: async (id) => {
      sent.push(id);
      return { status: 2 };
    },
  });
  assert.deepEqual(sent, ["ok-id"]);
  assert.equal(result.acked, true);
  assert.equal(result.attempts, 1);
});
