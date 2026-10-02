import { existsSync, readFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { config, ROOT_DIR } from "./config.js";
import { clearPendingAlert, readPendingAlert } from "../tools/owner-alert.js";

function ownerJid() {
  if (!config.ownerNumber) return null;
  return `${config.ownerNumber}@s.whatsapp.net`;
}

function readDownEvent() {
  const path = join(ROOT_DIR, "state", "down-event.json");
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function clearDownEvent() {
  const path = join(ROOT_DIR, "state", "down-event.json");
  if (existsSync(path)) unlinkSync(path);
}

export async function notifyOwnerRecovery(sock) {
  const jid = ownerJid();
  if (!jid) return;

  const down = readDownEvent();
  const pending = readPendingAlert();
  const lines = [];

  if (down?.downAt) {
    lines.push(`✅ WhatsApp Bot de nouveau en ligne.`);
    lines.push(`Panne détectée : ${down.downAt}`);
    if (down.host) lines.push(`Serveur : ${down.host}`);
  }
  if (pending?.text) {
    lines.push("");
    lines.push(pending.text);
  }

  if (!lines.length) return;

  try {
    await sock.sendMessage(jid, { text: lines.join("\n") });
    clearDownEvent();
    clearPendingAlert();
    console.log("Notification de reprise envoyée au propriétaire.");
  } catch (err) {
    console.error("Notification propriétaire :", err.message);
  }
}
