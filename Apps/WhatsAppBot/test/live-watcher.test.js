import assert from "node:assert/strict";
import test from "node:test";
import { activeWatcherCount, startLiveWatcher, stopLiveWatcher } from "../src/live-watcher.js";

test("un second démarrage remplace le watcher précédent", () => {
  const sock = {};
  const deps = {
    force: true,
    liveAnnounce: { enabled: true, pollSeconds: 60, confirmPolls: 4, modeFile: "unused" },
    readMode: () => "offline",
    fetchMode: async () => ({ ok: true, mode: "offline", title: "", reason: "test" }),
  };
  try {
    startLiveWatcher(sock, deps);
    startLiveWatcher(sock, deps);
    assert.equal(activeWatcherCount(), 1);
  } finally {
    stopLiveWatcher();
  }
  assert.equal(activeWatcherCount(), 0);
});
