import assert from "node:assert/strict";
import test from "node:test";
import { nextDelayMs, shouldStopReplaced } from "../src/reconnect.js";

test("les délais doublent et le 440 attend plus longtemps", () => {
  assert.equal(nextDelayMs(408, 1), 5_000);
  assert.equal(nextDelayMs(408, 2), 10_000);
  assert.equal(nextDelayMs(408, 3), 20_000);
  assert.equal(nextDelayMs(440, 1), 60_000);
  assert.equal(nextDelayMs(440, 2), 120_000);
  assert.equal(nextDelayMs(408, 20), 5 * 60_000);
});

test("trois 440 de suite arrêtent la reconnexion", () => {
  assert.equal(shouldStopReplaced(1), false);
  assert.equal(shouldStopReplaced(2), false);
  assert.equal(shouldStopReplaced(3), true);
});
