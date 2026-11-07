import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { isOwner, ROOT_DIR } from "./config.js";
import { displayPhone, isStatusJid } from "./text.js";

const STATE_PATH = join(ROOT_DIR, "state", "status-views.json");
const MAX_STORIES = 30;

function emptyState() {
  return { stories: {} };
}

function loadState() {
  if (!existsSync(STATE_PATH)) return emptyState();
  try {
    const data = JSON.parse(readFileSync(STATE_PATH, "utf8"));
    if (!data.stories || typeof data.stories !== "object") return emptyState();
    return data;
  } catch {
    return emptyState();
  }
}

function saveState(state) {
  const entries = Object.entries(state.stories).sort((a, b) =>
    String(b[1].at || "").localeCompare(String(a[1].at || ""))
  );
  state.stories = Object.fromEntries(entries.slice(0, MAX_STORIES));
  mkdirSync(join(ROOT_DIR, "state"), { recursive: true });
  writeFileSync(STATE_PATH, `${JSON.stringify(state, null, 2)}\n`);
}

function toIso(at) {
  let n = Number(at);
  if (!Number.isFinite(n) || n <= 0) n = Date.now();
  if (n < 1e12) n *= 1000;
  return new Date(n).toISOString();
}

function viewerLabel(jid) {
  const id = displayPhone(jid);
  if (String(jid).endsWith("@lid")) return `contact ${id.slice(-6)}`;
  return id;
}

export function rememberStory({ id, kind, at }) {
  if (!id) return;
  const state = loadState();
  const prev = state.stories[id] || { viewers: {} };
  state.stories[id] = {
    kind: kind || prev.kind || "statut",
    at: at || prev.at || new Date().toISOString(),
    viewers: prev.viewers || {},
  };
  saveState(state);
}

export function recordStatusView({ messageId, remoteJid, userJid, at }) {
  if (!messageId || !userJid) return false;
  if (remoteJid && !isStatusJid(remoteJid)) return false;
  if (isStatusJid(userJid) || isOwner(userJid)) return false;

  const state = loadState();
  const story = state.stories[messageId] || {
    kind: "statut",
    at: new Date().toISOString(),
    viewers: {},
  };
  if (story.viewers[userJid]) return false;
  story.viewers[userJid] = { at: toIso(at) };
  state.stories[messageId] = story;
  saveState(state);
  console.log(`Statut ouvert par ${viewerLabel(userJid)}`);
  return true;
}

export function formatStatusViews() {
  const stories = Object.entries(loadState().stories).sort((a, b) =>
    String(b[1].at || "").localeCompare(String(a[1].at || ""))
  );
  if (!stories.length) {
    return "Aucune ouverture enregistrée. Ça commence au prochain statut.";
  }

  const [, story] = stories[0];
  const when = new Date(story.at).toLocaleString("fr-FR", {
    timeZone: "Europe/Paris",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const kind =
    story.kind === "live" ? "début de live" : story.kind === "end" ? "fin de live" : "statut";
  const viewers = Object.entries(story.viewers || {}).sort((a, b) =>
    String(a[1].at).localeCompare(String(b[1].at))
  );
  const lines = [`*Vues du dernier statut*`, `${kind} — ${when}`];
  if (!viewers.length) {
    lines.push("Personne ne l’a encore ouvert.");
    return lines.join("\n");
  }
  lines.push(`${viewers.length} ouverture${viewers.length > 1 ? "s" : ""} :`);
  for (const [jid, info] of viewers) {
    const hour = new Date(info.at).toLocaleString("fr-FR", {
      timeZone: "Europe/Paris",
      hour: "2-digit",
      minute: "2-digit",
    });
    lines.push(`• ${viewerLabel(jid)} — ${hour}`);
  }
  return lines.join("\n");
}
