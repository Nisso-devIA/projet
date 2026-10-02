import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT_DIR } from "./config.js";

const CACHE_PATH = join(ROOT_DIR, "state", "contact-jids.json");
let jids = new Set();
let saveTimer = null;
let loaded = false;

function isIndividualJid(jid) {
  if (!jid || typeof jid !== "string") return false;
  if (jid === "status@broadcast") return false;
  if (jid.endsWith("@g.us")) return false;
  if (jid.endsWith("@broadcast")) return false;
  if (jid.endsWith("@lid")) return false;
  return jid.endsWith("@s.whatsapp.net");
}

function contactToJid(contact) {
  if (!contact) return null;
  if (contact.jid && isIndividualJid(contact.jid)) return contact.jid;
  if (contact.id && isIndividualJid(contact.id)) return contact.id;
  return null;
}

function loadCache() {
  if (loaded) return;
  loaded = true;
  if (!existsSync(CACHE_PATH)) return;
  try {
    const data = JSON.parse(readFileSync(CACHE_PATH, "utf8"));
    jids = new Set((data.jids || []).filter(isIndividualJid));
  } catch {
    /* ignore */
  }
}

function scheduleSave() {
  if (saveTimer) return;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
    writeFileSync(
      CACHE_PATH,
      `${JSON.stringify(
        { jids: [...jids], updatedAt: new Date().toISOString() },
        null,
        2
      )}\n`
    );
  }, 2000);
}

function addJids(list) {
  let changed = false;
  for (const jid of list) {
    if (isIndividualJid(jid) && !jids.has(jid)) {
      jids.add(jid);
      changed = true;
    }
  }
  if (changed) scheduleSave();
  return changed;
}

function addContacts(contacts) {
  const toAdd = [];
  for (const contact of contacts || []) {
    const jid = contactToJid(contact);
    if (jid) toAdd.push(jid);
  }
  return addJids(toAdd);
}

export function noteChatJid(jid) {
  return addJids([jid]);
}

export function getCachedContactCount() {
  loadCache();
  return jids.size;
}

export function getStatusAudienceJids(sock) {
  loadCache();
  const result = new Set(jids);
  if (sock?.user?.id) result.add(sock.user.id);
  return [...result];
}

export function bindContactCache(sock) {
  loadCache();

  sock.ev.on("messaging-history.set", ({ contacts, chats }) => {
    addContacts(contacts);
    if (chats?.length) addJids(chats.map((chat) => chat.id));
  });

  sock.ev.on("contacts.upsert", (contacts) => addContacts(contacts));
  sock.ev.on("contacts.update", (contacts) => addContacts(contacts));
  sock.ev.on("chats.upsert", (chats) => {
    if (chats?.length) addJids(chats.map((chat) => chat.id));
  });
}
