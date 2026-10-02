import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const STATE_DIR = join(ROOT, "state");
const ALERT_STATE_PATH = join(STATE_DIR, "alert-state.json");

dotenv.config({ path: join(ROOT, ".env") });

const ownerNumber = String(process.env.OWNER_NUMBER || "").replace(/\D/g, "");
const callMeBotKey = String(process.env.CALLMEBOT_APIKEY || "").trim();
const cooldownMs = Number(process.env.ALERT_COOLDOWN_MINUTES || 30) * 60_000;

function readState() {
  if (!existsSync(ALERT_STATE_PATH)) return {};
  try {
    return JSON.parse(readFileSync(ALERT_STATE_PATH, "utf8"));
  } catch {
    return {};
  }
}

function writeState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(ALERT_STATE_PATH, `${JSON.stringify(state, null, 2)}\n`);
}

function shouldSend(kind) {
  const state = readState();
  const last = Number(state[kind] || 0);
  return Date.now() - last > cooldownMs;
}

function markSent(kind) {
  const state = readState();
  state[kind] = Date.now();
  writeState(state);
}

export async function sendOwnerAlert(text, { kind = "down", force = false } = {}) {
  if (!ownerNumber) {
    console.error("OWNER_NUMBER manquant dans .env");
    return false;
  }
  if (!force && !shouldSend(kind)) {
    console.log(`Alerte ${kind} ignorée (cooldown)`);
    return false;
  }

  if (!callMeBotKey) {
    console.error("CALLMEBOT_APIKEY manquant — alerte WhatsApp impossible quand le bot est KO");
    writePendingAlert(text, kind);
    return false;
  }

  const url = new URL("https://api.callmebot.com/whatsapp.php");
  url.searchParams.set("phone", ownerNumber);
  url.searchParams.set("text", text);
  url.searchParams.set("apikey", callMeBotKey);

  const res = await fetch(url);
  const body = await res.text();
  if (!res.ok) {
    console.error(`CallMeBot ${res.status}: ${body.slice(0, 200)}`);
    writePendingAlert(text, kind);
    return false;
  }

  markSent(kind);
  console.log(`Alerte WhatsApp envoyée (${kind})`);
  return true;
}

function writePendingAlert(text, kind) {
  const path = join(STATE_DIR, "pending-owner-alert.json");
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(
    path,
    `${JSON.stringify({ text, kind, at: new Date().toISOString() }, null, 2)}\n`
  );
}

export function readPendingAlert() {
  const path = join(STATE_DIR, "pending-owner-alert.json");
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

export function clearPendingAlert() {
  const path = join(STATE_DIR, "pending-owner-alert.json");
  if (existsSync(path)) writeFileSync(path, "");
}

export function ownerJid() {
  if (!ownerNumber) return null;
  return `${ownerNumber}@s.whatsapp.net`;
}
