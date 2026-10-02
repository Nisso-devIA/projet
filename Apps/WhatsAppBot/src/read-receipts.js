import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { config, phoneFromJid, ROOT_DIR } from "./config.js";
import { displayPhone } from "./text.js";

const STATE_PATH = join(ROOT_DIR, "state", "read-tracker.json");
const NOTIFY_COOLDOWN_MS = 60_000;

let cache = null;
const lastNotifyAt = new Map();

function loadState() {
  if (cache) return cache;
  if (!existsSync(STATE_PATH)) {
    cache = { lastReads: {} };
    return cache;
  }
  try {
    cache = JSON.parse(readFileSync(STATE_PATH, "utf8"));
  } catch {
    cache = { lastReads: {} };
  }
  if (!cache.lastReads) cache.lastReads = {};
  return cache;
}

function saveState() {
  mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
  writeFileSync(STATE_PATH, `${JSON.stringify(cache, null, 2)}\n`);
}

export function isStealthChat(jid) {
  if (!config.stealthChats?.length) return false;
  return config.stealthChats.includes(phoneFromJid(jid));
}

export function shouldMarkIncomingAsRead(jid) {
  if (isStealthChat(jid)) return false;
  return Boolean(config.markAsRead);
}

export function shouldNotifyWhenTheyRead(jid) {
  if (!config.notifyOwnerOnRead) return false;
  if (isStealthChat(jid)) return true;
  if (!config.notifyOwnerOnReadChats?.length) return false;
  return config.notifyOwnerOnReadChats.includes(phoneFromJid(jid));
}

export function recordOutgoingRead(jid, key) {
  const state = loadState();
  const phone = displayPhone(jid);
  state.lastReads[phone] = {
    jid,
    messageId: key.id,
    at: new Date().toISOString(),
  };
  saveState();
}

export function getLastReads() {
  const state = loadState();
  return state.lastReads;
}

export function formatLastReads() {
  const entries = Object.entries(getLastReads());
  if (!entries.length) return "Aucune lecture enregistrée pour l'instant.";
  const lines = ["*Dernières lectures de tes messages*"];
  for (const [phone, info] of entries.slice(-10).reverse()) {
    lines.push(`• ${phone} — lu le ${new Date(info.at).toLocaleString("fr-FR", { timeZone: "Europe/Paris" })}`);
  }
  return lines.join("\n");
}

function ownerJid() {
  if (!config.ownerNumber) return null;
  return `${config.ownerNumber}@s.whatsapp.net`;
}

export async function notifyOwnerOutgoingRead(sock, jid, key) {
  if (!shouldNotifyWhenTheyRead(jid)) return;

  const phone = phoneFromJid(jid);
  const now = Date.now();
  const last = lastNotifyAt.get(phone) || 0;
  if (now - last < NOTIFY_COOLDOWN_MS) return;
  lastNotifyAt.set(phone, now);

  recordOutgoingRead(jid, key);

  const target = ownerJid();
  if (!target) {
    console.log(`[lecture] ${phone} a lu ton message`);
    return;
  }

  const when = new Date().toLocaleString("fr-FR", {
    timeZone: "Europe/Paris",
    hour: "2-digit",
    minute: "2-digit",
  });
  const text = `👀 *Lu* · ${phone}\nTes messages ont été lus à ${when}.`;

  try {
    await sock.sendMessage(target, { text });
    console.log(`Alerte lecture envoyée pour ${phone}`);
  } catch (err) {
    console.error("Alerte lecture :", err.message);
  }
}
