import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { generateMessageIDV2 } from "@whiskeysockets/baileys";
import { config, ROOT_DIR } from "./config.js";
import { getCachedContactCount, getStatusAudienceJids } from "./contact-cache.js";
import { createStatusRetry, isServerAck, watchStatusDelivery } from "./status-ack.js";
import {
  ensureStatusSessions,
  refreshStatusDevices,
  resolveStatusRecipients,
  statusRecipients,
  deliverStatus,
} from "./status-send.js";
import { rememberStory } from "./status-views.js";

const retries = createStatusRetry();
const ACK_TIMEOUT_MS = 20_000;

const STATE_PATH = join(ROOT_DIR, "state", "last-live-status.json");
const RATE_PATH = join(ROOT_DIR, "state", "story-rate.json");

function phoneFromJid(jid) {
  return String(jid || "").split("@")[0].split(":")[0];
}

function getExcludedStoryPhones() {
  const la = config.liveAnnounce || {};
  return new Set([...(la.statusExcludeList || [])]);
}

function applyStoryExclusions(jids) {
  const excluded = getExcludedStoryPhones();
  if (!excluded.size) return jids;
  return jids.filter((jid) => !excluded.has(phoneFromJid(jid)));
}

function buildStatusJidList(sock) {
  const la = config.liveAnnounce || {};
  const audience = la.statusAudience || "all";
  const raw = [];
  if (audience === "custom") {
    raw.push(...(la.statusJidList || []).map((phone) => `${phone}@s.whatsapp.net`));
  } else {
    raw.push(...getStatusAudienceJids(sock));
    for (const phone of la.statusJidList || []) raw.push(`${phone}@s.whatsapp.net`);
  }
  if (config.ownerNumber) raw.push(`${config.ownerNumber}@s.whatsapp.net`);
  if (sock.user?.id) raw.push(sock.user.id);
  return statusRecipients(applyStoryExclusions(raw), sock.user?.id);
}

function readLastPosted() {
  if (!existsSync(STATE_PATH)) return null;
  try {
    return JSON.parse(readFileSync(STATE_PATH, "utf8"));
  } catch {
    return null;
  }
}

function writeLastPosted(kind) {
  mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
  writeFileSync(
    STATE_PATH,
    `${JSON.stringify({ kind, at: new Date().toISOString() }, null, 2)}\n`
  );
}

function readStoryRate() {
  if (!existsSync(RATE_PATH)) return [];
  try {
    const data = JSON.parse(readFileSync(RATE_PATH, "utf8"));
    return Array.isArray(data.posts) ? data.posts : [];
  } catch {
    return [];
  }
}

function recordStoryPost() {
  const now = Date.now();
  const dayAgo = now - 24 * 60 * 60 * 1000;
  const posts = [...readStoryRate(), now].filter((ts) => ts > dayAgo);
  mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
  writeFileSync(RATE_PATH, `${JSON.stringify({ posts }, null, 2)}\n`);
}

function assertStoryRateLimit() {
  const max = config.liveAnnounce?.maxStoriesPerDay ?? 4;
  const recent = readStoryRate().filter((ts) => ts > Date.now() - 24 * 60 * 60 * 1000);
  if (recent.length >= max) {
    throw new Error(`Limite story atteinte (${max}/24h) — pas de spam`);
  }
}

export async function postTextStatus(sock, text, options = {}) {
  const { backgroundColor, font } = options;
  const la = config.liveAnnounce || {};
  if (!la.enabled) {
    throw new Error("Stories désactivées dans la config");
  }
  if (options.countSlot !== false) assertStoryRateLimit();
  const phoneList = buildStatusJidList(sock);
  const mapping = sock.signalRepository?.lidMapping;
  const audience = await resolveStatusRecipients(phoneList, {
    getLids: mapping?.getLIDsForPNs?.bind(mapping),
    ownLid: sock.user?.lid || sock.authState?.creds?.me?.lid,
  });
  const statusJidList = audience.recipients;
  console.log(
    `Story audience : ${phoneList.length} numéros, mode ${audience.mode}, LID ${audience.resolved}, sans LID ${audience.unresolved}`
  );

  if (statusJidList.length < 1) {
    throw new Error(
      "Aucun contact pour la story — laisse le bot connecté quelques minutes pour synchroniser les contacts"
    );
  }

  const messageId = options.messageId || generateMessageIDV2(sock.user?.id);
  const maxAttempts = options.maxAttempts || (options.messageId ? 1 : 2);
  const content = {
    text,
    contextInfo: {
      featureEligibilities: { canBeReshared: true },
    },
  };
  const sendOptions = {
    broadcast: true,
    statusJidList,
    backgroundColor: backgroundColor || la.liveBackgroundColor || "#9146FF",
    font: font ?? la.statusFont ?? 2,
    messageId,
  };
  const refresh = async () => {
    const fetched = await refreshStatusDevices(sock.getUSyncDevices?.bind(sock), statusJidList);
    const sessions = await ensureStatusSessions(sock.assertSessions?.bind(sock), fetched.deviceJids);
    console.log(
      `Story préparation : ${statusJidList.length} destinataires, ${fetched.chunks} lots, ${fetched.devices} appareils, ${fetched.failedChunks} lots en échec, sessions ${sessions.failedChunks} échecs`
    );
    return fetched;
  };
  if (options.countSlot !== false) recordStoryPost();
  const delivered = await deliverStatus({
    createId: () => messageId,
    maxAttempts,
    refresh,
    waitAck: (id) => watchStatusDelivery(sock.ev, id, ACK_TIMEOUT_MS),
    send: async (id) => {
      const result = await sock.sendMessage("status@broadcast", content, { ...sendOptions, messageId: id });
      return { status: result?.status ?? null, result };
    },
  });
  const delivery = delivered.status;
  const acked = delivered.acked && isServerAck(delivery);
  console.log(
    `Story ${acked ? "confirmée" : "non confirmée"} id=${delivered.id} essais=${delivered.attempts} (${statusJidList.length} contacts, ${getExcludedStoryPhones().size} exclus, statut=${delivery ?? "?"}, cache=${getCachedContactCount()})`
  );
  if (delivery === 479) {
    console.warn(`Story ${delivered.id} refusée par WhatsApp (ack 479).`);
  } else if (!acked) {
    console.warn(`Story ${delivered.id} sans accusé de remise après ${delivered.attempts} essai(s) du même id.`);
  }

  return {
    result: { key: { id: delivered.id }, status: delivery },
    statusJidList,
    delivery,
    acked,
    contactCount: getCachedContactCount(),
  };
}

export async function postLiveStory(sock, title = "", options = {}) {
  const la = config.liveAnnounce || {};
  const url = la.twitchUrl || "https://twitch.tv/zaeldryk";
  const base = la.liveStatusText || "🔴 Zaeldryk est EN LIVE !";
  const text = title ? `${base}\n${title}\n${url}` : `${base}\n${url}`;

  const info = await postTextStatus(sock, text, {
    backgroundColor: la.liveBackgroundColor || "#9146FF",
    font: la.statusFont ?? 2,
    countSlot: options.countSlot,
    messageId: options.messageId,
    maxAttempts: options.maxAttempts,
  });
  if (!info.acked) {
    scheduleStatusRetry("live", title, info.result?.key?.id);
    return info;
  }
  rememberStory({
    id: info.result?.key?.id,
    kind: "live",
    at: new Date().toISOString(),
  });
  writeLastPosted("live");
  retries.clear();
  return info;
}

export async function postEndStory(sock, options = {}) {
  const la = config.liveAnnounce || {};
  const text =
    la.endStatusText || "✅ Live terminé — merci d'avoir regardé ! À bientôt 👋";

  const info = await postTextStatus(sock, text, {
    backgroundColor: la.endBackgroundColor || "#1a1a2e",
    font: la.statusFont ?? 2,
    countSlot: options.countSlot,
    messageId: options.messageId,
    maxAttempts: options.maxAttempts,
  });
  if (!info.acked) {
    scheduleStatusRetry("end", "", info.result?.key?.id);
    return info;
  }
  rememberStory({
    id: info.result?.key?.id,
    kind: "end",
    at: new Date().toISOString(),
  });
  writeLastPosted("end");
  retries.clear();
  return info;
}

export async function postTestStory(sock) {
  const la = config.liveAnnounce || {};
  const text = la.testStatusText || "🧪 Test story WhatsApp Bot — tout fonctionne !";
  const info = await postTextStatus(sock, text, {
    backgroundColor: "#128C7E",
    font: la.statusFont ?? 2,
  });
  rememberStory({
    id: info.result?.key?.id,
    kind: "test",
    at: new Date().toISOString(),
  });
  return info;
}

export function getLastPostedKind() {
  return readLastPosted()?.kind || null;
}

export function scheduleStatusRetry(kind, title, messageId) {
  const result = retries.schedule(kind, title, messageId);
  if (result === "exhausted") {
    console.log(`Story ${kind} non confirmée après le second essai. Aucun autre envoi.`);
  }
  return result;
}

export async function runPendingStatusRetry(sock) {
  const job = retries.take();
  if (!job || !sock) return null;
  console.log(`Reprise de la story ${job.kind} avec le même id`);
  const retryOptions = { countSlot: false, messageId: job.messageId, maxAttempts: 1 };
  try {
    if (job.kind === "end") return await postEndStory(sock, retryOptions);
    return await postLiveStory(sock, job.title || "", retryOptions);
  } catch (err) {
    scheduleStatusRetry(job.kind, job.title || "", job.messageId);
    console.error(`Reprise story ${job.kind} échouée : ${err.message}`);
    return null;
  }
}
