import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT_DIR } from "./config.js";

export const HEARTBEAT_PATH = join(ROOT_DIR, "state", "heartbeat.json");

let timer = null;
let lastStatus = "starting";

export function writeHeartbeat(status, extra = {}) {
  lastStatus = status;
  const payload = {
    pid: process.pid,
    status,
    updatedAt: new Date().toISOString(),
    updatedMs: Date.now(),
    ...extra,
  };
  mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
  writeFileSync(HEARTBEAT_PATH, `${JSON.stringify(payload, null, 2)}\n`);
}

export function startHeartbeat(status = "connected") {
  writeHeartbeat(status);
  if (timer) clearInterval(timer);
  timer = setInterval(() => writeHeartbeat(lastStatus), 15_000);
}

export function stopHeartbeat(status = "disconnected") {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  writeHeartbeat(status);
}
