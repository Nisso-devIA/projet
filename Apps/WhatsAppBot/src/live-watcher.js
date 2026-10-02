import { existsSync, readFileSync } from "node:fs";
import { config } from "./config.js";
import { getLastPostedKind, postEndStory, postLiveStory } from "./status-post.js";
import { fetchTwitchStreamMode } from "./twitch-live.js";

/**
 * Stories live basées sur un VRAI live Twitch :
 * - Helix stream ON
 * - titre SANS mots-clés offline/ending/brb/fin de live/hors ligne
 * Le faux live (titre offline) = mode ending → jamais de story "en live".
 */
export function startLiveWatcher(sock) {
  const la = config.liveAnnounce;
  if (!la?.enabled) {
    console.log("Live watcher désactivé (liveAnnounce.enabled = false)");
    return;
  }

  const modeFile = la.modeFile;
  if (!modeFile || !existsSync(modeFile)) {
    console.log(`Live watcher désactivé (fichier absent : ${modeFile || "?"})`);
    return;
  }

  const confirmPolls = Math.max(2, Number(la.confirmPolls || 4));
  let lastMode = normalizeMode(readMode(modeFile));
  let liveStreak = 0;
  let announcedLive = false;
  let sawFakeOrOffline = isFakeOrOffline(lastMode);
  let posting = false;

  if (lastMode === "live" && getLastPostedKind() === "live") {
    announcedLive = true;
    liveStreak = confirmPolls;
  }

  console.log(
    `Live watcher actif (mode=${lastMode}, confirm=${confirmPolls}, vérif titre offline, announcedLive=${announcedLive})`
  );

  setInterval(async () => {
    if (posting) return;
    try {
      const fileMode = normalizeMode(readMode(modeFile));
      let mode = fileMode;
      let title = "";

      // Double check Helix + titre (texte offline = faux live)
      try {
        const helix = await fetchTwitchStreamMode();
        if (helix.ok && helix.mode) {
          mode = helix.mode;
          title = helix.title || "";
          if (helix.mode !== fileMode) {
            console.log(
              `Twitch check: fichier=${fileMode} helix=${helix.mode} (${helix.reason}) title="${truncate(title)}"`
            );
          }
        }
      } catch (err) {
        console.error("Twitch check :", err.message);
      }

      if (mode === "live") {
        liveStreak += 1;
      } else {
        liveStreak = 0;
        if (isFakeOrOffline(mode)) sawFakeOrOffline = true;
      }

      // Story LIVE : vrai live confirmé, après avoir vu offline/ending (faux live)
      if (
        mode === "live" &&
        sawFakeOrOffline &&
        liveStreak >= confirmPolls &&
        !announcedLive
      ) {
        posting = true;
        try {
          await postLiveStory(sock, title);
          announcedLive = true;
          console.log(
            `Story LIVE publiée (vrai live confirmé ${confirmPolls}×, titre="${truncate(title)}")`
          );
        } finally {
          posting = false;
        }
      }

      if (mode === lastMode) return;

      const prev = lastMode;
      lastMode = mode;
      console.log(`Twitch mode: ${prev} → ${mode}${title ? ` | ${truncate(title)}` : ""}`);

      // Ignore bruit ending ↔ offline (faux live / pas de stream)
      if (isFakeOrOffline(prev) && isFakeOrOffline(mode)) return;

      // Story FIN : seulement après une story live, quand titre offline ou stream off
      if (
        announcedLive &&
        prev === "live" &&
        isFakeOrOffline(mode)
      ) {
        posting = true;
        try {
          await postEndStory(sock);
          announcedLive = false;
          console.log(
            `Story FIN DE LIVE publiée (raison=${mode}${title ? `, titre="${truncate(title)}"` : ""})`
          );
        } finally {
          posting = false;
        }
      }
    } catch (err) {
      posting = false;
      console.error("Live watcher :", err.message);
    }
  }, (la.pollSeconds || 15) * 1000);
}

function isFakeOrOffline(mode) {
  return mode === "ending" || mode === "offline" || mode === "none";
}

function normalizeMode(raw) {
  const mode = String(raw || "none").trim().toLowerCase();
  if (["live", "ending", "offline", "none"].includes(mode)) return mode;
  return "none";
}

function readMode(path) {
  try {
    return readFileSync(path, "utf8").trim() || "none";
  } catch {
    return "none";
  }
}

function truncate(text, max = 60) {
  const s = String(text || "");
  return s.length > max ? `${s.slice(0, max)}…` : s;
}
