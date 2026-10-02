import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { config, ROOT_DIR } from "./config.js";
import { getCachedContactCount, getStatusAudienceJids } from "./contact-cache.js";

const STATE_PATH = join(ROOT_DIR, "state", "last-live-status.json");
const RATE_PATH = join(ROOT_DIR, "state", "story-rate.json");

function phoneFromJid(jid) {
  return String(jid || "").split("@")[0].split(":")[0];
}

function getExcludedStoryPhones() {
  const la = config.liveAnnounce || {};
  return new Set([
    ...(config.stealthChats || []),
    ...(la.statusExcludeList || []),
  ]);
}

function applyStoryExclusions(jids) {
  const excluded = getExcludedStoryPhones();
  if (!excluded.size) return jids;
  return jids.filter((jid) => !excluded.has(phoneFromJid(jid)));
}

function buildStatusJidList(sock) {
  const la = config.liveAnnounce || {};
  const audience = la.statusAudience || "all";
  let jids;

  if (audience === "custom") {
    const phones = new Set(la.statusJidList || []);
    if (config.ownerNumber) phones.add(config.ownerNumber);
    jids = [...phones].map((p) => `${p}@s.whatsapp.net`);
    if (sock.user?.id) jids.unshift(sock.user.id);
    jids = [...new Set(jids)];
  } else {
    jids = new Set(getStatusAudienceJids(sock));
    for (const phone of la.statusJidList || []) {
      jids.add(`${phone}@s.whatsapp.net`);
    }
    if (config.ownerNumber) {
      jids.add(`${config.ownerNumber}@s.whatsapp.net`);
    }
    jids = [...jids];
  }

  return applyStoryExclusions(jids);
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
  recordStoryPost();
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

export async function postTextStatus(sock, text, { backgroundColor, font } = {}) {
  const la = config.liveAnnounce || {};
  if (!la.enabled) {
    throw new Error("Stories désactivées dans la config");
  }
  assertStoryRateLimit();
  const statusJidList = buildStatusJidList(sock);

  if (statusJidList.length < 1) {
    throw new Error(
      "Aucun contact pour la story — laisse le bot connecté quelques minutes pour synchroniser les contacts"
    );
  }

  const result = await sock.sendMessage(
    "status@broadcast",
    {
      text,
      contextInfo: {
        featureEligibilities: { canBeReshared: true },
      },
    },
    {
      broadcast: true,
      statusJidList,
      backgroundColor: backgroundColor || la.liveBackgroundColor || "#9146FF",
      font: font ?? la.statusFont ?? 2,
    }
  );

  const delivery = result?.status || "inconnu";
  console.log(
    `Story envoyée (${statusJidList.length} contacts, ${getExcludedStoryPhones().size} exclus, statut=${delivery}, cache=${getCachedContactCount()})`
  );

  if (delivery === "PENDING" || delivery === 0) {
    console.warn(
      "Story en attente — bug connu Baileys : peut ne pas apparaître sur le téléphone"
    );
  }

  return { result, statusJidList, delivery, contactCount: getCachedContactCount() };
}

export async function postLiveStory(sock, title = "") {
  const la = config.liveAnnounce || {};
  const url = la.twitchUrl || "https://twitch.tv/zaeldryk";
  const base = la.liveStatusText || "🔴 Zaeldryk est EN LIVE !";
  const text = title ? `${base}\n${title}\n${url}` : `${base}\n${url}`;

  await postTextStatus(sock, text, {
    backgroundColor: la.liveBackgroundColor || "#9146FF",
    font: la.statusFont ?? 2,
  });
  writeLastPosted("live");
}

export async function postEndStory(sock) {
  const la = config.liveAnnounce || {};
  const text =
    la.endStatusText || "✅ Live terminé — merci d'avoir regardé ! À bientôt 👋";

  await postTextStatus(sock, text, {
    backgroundColor: la.endBackgroundColor || "#1a1a2e",
    font: la.statusFont ?? 2,
  });
  writeLastPosted("end");
}

export async function postTestStory(sock) {
  const la = config.liveAnnounce || {};
  const text = la.testStatusText || "🧪 Test story WhatsApp Bot — tout fonctionne !";
  return postTextStatus(sock, text, {
    backgroundColor: "#128C7E",
    font: la.statusFont ?? 2,
  });
}

export function getLastPostedKind() {
  return readLastPosted()?.kind || null;
}
