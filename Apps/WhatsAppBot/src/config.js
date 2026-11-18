import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
dotenv.config({ path: join(ROOT, ".env") });

const defaults = {
  botName: "WhatsApp Bot",
  prefix: "!",
  ignoreGroups: false,
  ignoreStatus: true,
  markAsRead: false,
  showTyping: false,
  transcribeVoice: false,
  transcribeMode: "command",
  transcribeAllowList: [],
  transcribeReplyInChat: true,
  transcribeLanguage: "fr",
  autoRepliesEnabled: false,
  allowProactiveChatMessages: false,
  commandsOwnerOnly: true,
  autoReplies: [],
  liveAnnounce: {
    enabled: false,
    modeFile: "/home/ubuntu/zaeldryk/state/mode.txt",
    pollSeconds: 15,
    confirmPolls: 4,
    twitchEnvFile: "/home/ubuntu/zaeldryk/config/twitch.env",
    liveEnvFile: "/home/ubuntu/zaeldryk/config/live.env",
    twitchUrl: "https://twitch.tv/zaeldryk",
    liveStatusText: "🔴 Zaeldryk est EN LIVE !",
    endStatusText: "✅ Live terminé — merci d'avoir regardé ! À bientôt 👋",
    liveBackgroundColor: "#9146FF",
    endBackgroundColor: "#1a1a2e",
    statusFont: 2,
    statusAudience: "all",
    statusExcludeList: [],
    statusJidList: [],
    maxStoriesPerDay: 4,
  },
};

function loadJson() {
  const path = join(ROOT, "config.json");
  if (!existsSync(path)) return {};
  return JSON.parse(readFileSync(path, "utf8"));
}

function normalizePhone(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeAllowList(list) {
  return (list || []).map(normalizePhone).filter(Boolean);
}

const fileConfig = loadJson();

export const ROOT_DIR = ROOT;
export const AUTH_DIR = join(ROOT, "auth_info");

export const config = {
  ...defaults,
  ...fileConfig,
  transcribeAllowList: normalizeAllowList(fileConfig.transcribeAllowList),
  liveAnnounce: {
    ...defaults.liveAnnounce,
    ...(fileConfig.liveAnnounce || {}),
    statusJidList: normalizeAllowList(fileConfig.liveAnnounce?.statusJidList),
    statusExcludeList: normalizeAllowList(fileConfig.liveAnnounce?.statusExcludeList),
  },
  ownerNumber: normalizePhone(process.env.OWNER_NUMBER),
  pairingNumber: normalizePhone(process.env.PAIRING_NUMBER),
  groqKey: String(process.env.GROQ_API_KEY || "").trim(),
  openaiKey: String(process.env.OPENAI_API_KEY || "").trim(),
};

export function phoneFromJid(jid) {
  return String(jid || "").split("@")[0].split(":")[0];
}

export function isOwner(jid) {
  if (!config.ownerNumber) return false;
  return phoneFromJid(jid) === config.ownerNumber;
}

export function isTranscribeAllowlisted(jid) {
  if (!config.transcribeAllowList.length) return false;
  return config.transcribeAllowList.includes(phoneFromJid(jid));
}

export function shouldAutoTranscribe(jid) {
  if (!config.transcribeVoice) return false;
  const mode = config.transcribeMode || "command";
  if (mode === "off" || mode === "command") return false;
  if (mode === "all") return true;
  if (mode === "allowlist") return isTranscribeAllowlisted(jid);
  return false;
}
