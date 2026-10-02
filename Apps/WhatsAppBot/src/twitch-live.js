import { existsSync, readFileSync } from "node:fs";
import { config } from "./config.js";

const DEFAULT_OFFLINE_PATTERN =
  "offline|ending|brb|fin de live|hors ligne";

function loadTwitchEnv() {
  const la = config.liveAnnounce || {};
  const envPath = la.twitchEnvFile || "/home/ubuntu/zaeldryk/config/twitch.env";
  const liveEnvPath = la.liveEnvFile || "/home/ubuntu/zaeldryk/config/live.env";
  const env = {};

  for (const path of [envPath, liveEnvPath]) {
    if (!existsSync(path)) continue;
    for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq < 0) continue;
      const key = trimmed.slice(0, eq).trim();
      let value = trimmed.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      env[key] = value;
    }
  }

  return {
    clientId: env.TWITCH_CLIENT_ID || "",
    broadcasterId: env.TWITCH_BROADCASTER_ID || "426411773",
    tokenFile: env.TWITCH_TOKEN_FILE || "/home/ubuntu/twitch_token.txt",
    offlinePattern: env.OFFLINE_PATTERN || DEFAULT_OFFLINE_PATTERN,
  };
}

function titleLooksOffline(title, pattern) {
  const titleLc = String(title || "").toLowerCase();
  if (!titleLc) return false;
  try {
    return new RegExp(pattern, "i").test(titleLc);
  } catch {
    return /offline|ending|brb|fin de live|hors ligne/i.test(titleLc);
  }
}

/**
 * Vérifie Helix Twitch : vrai live = stream ON + titre SANS mot-clé offline.
 * ending = stream ON + titre offline/brb/...
 * offline = pas de stream Helix.
 */
export async function fetchTwitchStreamMode() {
  const tw = loadTwitchEnv();
  if (!tw.clientId || !existsSync(tw.tokenFile)) {
    return { ok: false, mode: null, title: "", reason: "twitch_env_missing" };
  }

  let token = "";
  try {
    token = readFileSync(tw.tokenFile, "utf8").trim();
  } catch {
    return { ok: false, mode: null, title: "", reason: "token_unreadable" };
  }
  if (!token) {
    return { ok: false, mode: null, title: "", reason: "token_empty" };
  }

  const url = `https://api.twitch.tv/helix/streams?user_id=${encodeURIComponent(tw.broadcasterId)}`;
  const res = await fetch(url, {
    headers: {
      "Client-ID": tw.clientId,
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    return {
      ok: false,
      mode: null,
      title: "",
      reason: `helix_${res.status}`,
    };
  }

  const data = await res.json();
  const stream = data?.data?.[0];
  if (!stream) {
    return { ok: true, mode: "offline", title: "", reason: "no_stream" };
  }

  const title = String(stream.title || "");
  if (titleLooksOffline(title, tw.offlinePattern)) {
    return { ok: true, mode: "ending", title, reason: "title_offline" };
  }

  return { ok: true, mode: "live", title, reason: "real_live" };
}
