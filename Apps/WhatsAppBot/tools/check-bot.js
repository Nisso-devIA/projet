import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const HEARTBEAT_PATH = join(ROOT, "state", "heartbeat.json");
const STALE_MS = 90_000;

function listBotPidsWindows() {
  try {
    const out = execFileSync(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", join(ROOT, "tools", "list-bot-pids.ps1")],
      { encoding: "utf8", windowsHide: true }
    ).trim();
    return parsePids(out);
  } catch {
    return [];
  }
}

function listBotPidsLinux() {
  try {
    const out = execFileSync("pgrep", ["-f", "whatsapp-bot/src/index.js"], {
      encoding: "utf8",
    }).trim();
    return parsePids(out.replace(/\s+/g, ","));
  } catch {
    return [];
  }
}

function parsePids(out) {
  if (!out) return [];
  return out
    .split(/[,\s]+/)
    .map((x) => Number(x.trim()))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function listBotPids() {
  return process.platform === "win32" ? listBotPidsWindows() : listBotPidsLinux();
}

function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function readHeartbeat() {
  if (!existsSync(HEARTBEAT_PATH)) return null;
  try {
    return JSON.parse(readFileSync(HEARTBEAT_PATH, "utf8"));
  } catch {
    return null;
  }
}

const pids = listBotPids();
const hb = readHeartbeat();
const now = Date.now();
const ageMs = hb?.updatedMs ? now - Number(hb.updatedMs) : null;
const ageSec = ageMs == null ? null : Math.max(0, Math.round(ageMs / 1000));
const hbAlive = hb?.pid ? pidAlive(hb.pid) : false;
const stale = ageMs == null || ageMs > STALE_MS;
const processUp = pids.length > 0 || hbAlive;
const waConnected = Boolean(hb && hb.status === "connected" && !stale && hbAlive);

let state = "DOWN";
let exitCode = 1;
if (processUp && waConnected) {
  state = "OK";
  exitCode = 0;
} else if (processUp && !stale) {
  state = "WARN";
  exitCode = 2;
}

const lines = [
  `etat        ${state}`,
  `processus   ${processUp ? "oui" : "non"}${pids.length ? `  pid=${pids.join(",")}` : ""}`,
  `whatsapp    ${waConnected ? "connecté" : hb?.status || "inconnu"}`,
];
if (hb) {
  lines.push(`heartbeat   ${hb.updatedAt || "?"}  (il y a ${ageSec}s)`);
} else {
  lines.push("heartbeat   absent");
}

console.log(lines.join("\n"));
process.exit(exitCode);
