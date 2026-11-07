import makeWASocket, {
  Browsers,
  DisconnectReason,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
  WAMessageStatus,
} from "@whiskeysockets/baileys";
import { Boom } from "@hapi/boom";
import { existsSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import pino from "pino";
import QRCode from "qrcode";
import qrcode from "qrcode-terminal";
import { AUTH_DIR, ROOT_DIR, config, isOwner, shouldAutoTranscribe } from "./config.js";
import { handleCommand, matchAutoReply } from "./commands.js";
import { sendChatReply } from "./chat-send.js";
import { noteChatJid } from "./contact-cache.js";
import { formatTranscript, transcribeAudioBuffer, warmupWhisper } from "./transcribe.js";
import { startHeartbeat, stopHeartbeat, writeHeartbeat } from "./heartbeat.js";
import { notifyOwnerRecovery } from "./owner-notify.js";
import { bindContactCache } from "./contact-cache.js";
import { startLiveWatcher } from "./live-watcher.js";
import { recordStatusView } from "./status-views.js";
import {
  notifyOwnerOutgoingRead,
  shouldMarkIncomingAsRead,
} from "./read-receipts.js";
import {
  buildQuotedDownloadMessage,
  getAudioMessage,
  getMessageText,
  isEmptyContent,
  isGroupJid,
  isRecentMessage,
  isStatusJid,
  messageTypeKeys,
} from "./text.js";

const logger = pino({ level: "silent" });

let starting = false;
let reconnectTimer = null;
let sessionId = 0;
let currentSock = null;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function scheduleReconnect(delayMs) {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    startBot().catch((err) => {
      console.error("Échec de reconnexion :", err);
      process.exit(1);
    });
  }, delayMs);
}

async function closeSocket(sock) {
  if (!sock) return;
  try {
    sock.ev.removeAllListeners();
  } catch {
    /* ignore */
  }
  try {
    sock.end(undefined);
  } catch {
    /* ignore */
  }
}

async function startBot() {
  if (starting) return;
  starting = true;
  const id = ++sessionId;

  if (currentSock) {
    await closeSocket(currentSock);
    currentSock = null;
    await delay(2000);
  }

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    logger,
    browser: process.platform === "win32" ? Browsers.windows("Chrome") : Browsers.ubuntu("Chrome"),
    markOnlineOnConnect: false,
    syncFullHistory: true,
  });
  currentSock = sock;
  bindContactCache(sock);

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    if (id !== sessionId) return;

    const { connection, lastDisconnect, qr } = update;
    const alreadyLinked = Boolean(sock.authState?.creds?.me);

    if (qr && !config.pairingNumber && !alreadyLinked) {
      const qrPath = join(ROOT_DIR, "qr.png");
      console.log("\nScanne ce QR : WhatsApp → Appareils liés → Lier un appareil");
      console.log(`Image : ${qrPath}\n`);
      qrcode.generate(qr, { small: true });
      await QRCode.toFile(qrPath, qr, { width: 360, margin: 2 });
    }

    if (connection === "connecting") {
      console.log("Connexion à WhatsApp…");
      writeHeartbeat("connecting");
    }

    if (connection === "open") {
      const qrPath = join(ROOT_DIR, "qr.png");
      if (existsSync(qrPath)) unlinkSync(qrPath);
      console.log(`Connecté. Bot prêt. Préfixe : ${config.prefix}`);
      startHeartbeat("connected");
      if (config.transcribeVoice || config.transcribeMode === "command") warmupWhisper();
      await notifyOwnerRecovery(sock);
      startLiveWatcher(sock);
    }

    if (connection === "close") {
      starting = false;
      stopHeartbeat("disconnected");
      const error = lastDisconnect?.error;
      const status = error instanceof Boom ? error.output.statusCode : undefined;

      if (status === DisconnectReason.loggedOut) {
        console.error(
          "Session expirée. Supprime le dossier auth_info puis relance : npm start"
        );
        process.exit(1);
      }

      const delayMs = status === DisconnectReason.connectionReplaced ? 25000 : 5000;
      console.log(`Déconnecté (${status ?? "?"}), reconnexion dans ${delayMs / 1000}s…`);
      scheduleReconnect(delayMs);
    }
  });

  if (config.pairingNumber && !sock.authState.creds.registered) {
    await delay(2000);
    try {
      const code = await sock.requestPairingCode(config.pairingNumber);
      console.log(`\nCode de jumelage : ${code}`);
      console.log("WhatsApp → Appareils liés → Lier un appareil → Lier avec un numéro\n");
    } catch (err) {
      console.error("Impossible de générer le code de jumelage :", err.message);
    }
  }

  sock.ev.on("message-receipt.update", (updates) => {
    if (id !== sessionId) return;
    for (const { key, receipt } of updates || []) {
      if (!receipt?.readTimestamp) continue;
      try {
        recordStatusView({
          messageId: key?.id,
          remoteJid: key?.remoteJid,
          userJid: receipt.userJid,
          at: receipt.readTimestamp,
        });
      } catch (err) {
        console.error("Vue statut :", err.message);
      }
    }
  });

  sock.ev.on("messages.update", async (updates) => {
    if (id !== sessionId) return;
    for (const { key, update } of updates) {
      if (!key?.fromMe || !key.remoteJid) continue;
      if (update.status !== WAMessageStatus.READ && update.status !== WAMessageStatus.PLAYED) {
        continue;
      }
      try {
        await notifyOwnerOutgoingRead(sock, key.remoteJid, key);
      } catch (err) {
        console.error("Erreur lecture sortante :", err.message);
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (id !== sessionId) return;
    if (type !== "notify" && type !== "append") return;

    for (const msg of messages) {
      try {
        await onMessage(sock, msg, type);
      } catch (err) {
        console.error("Erreur message :", err.message);
      }
    }
  });
}

const seenIds = new Set();

function alreadySeen(id) {
  if (!id) return false;
  if (seenIds.has(id)) return true;
  seenIds.add(id);
  if (seenIds.size > 400) {
    const first = seenIds.values().next().value;
    seenIds.delete(first);
  }
  return false;
}

async function transcribeVoice(sock, sourceMsg, jid, audio, { quotedMsg = null } = {}) {
  const pushName = sourceMsg.pushName || "";
  console.log(`[${pushName || jid}] (vocal ${audio.seconds || "?"}s)`);
  if (shouldMarkIncomingAsRead(jid)) {
    await sock.readMessages([sourceMsg.key]).catch(() => {});
  }
  await sock.sendPresenceUpdate("composing", jid).catch(() => {});
  try {
    const buffer = await downloadMediaMessage(
      sourceMsg,
      "buffer",
      {},
      { logger, reuploadRequest: sock.updateMediaMessage }
    );
    const text = await transcribeAudioBuffer(buffer, audio.mimetype);
    const body = formatTranscript({ pushName, seconds: audio.seconds, text });
    const targetJid =
      config.transcribeReplyInChat || !config.ownerNumber
        ? jid
        : `${config.ownerNumber}@s.whatsapp.net`;
    await sendChatReply(
      sock,
      targetJid,
      { text: config.transcribeReplyInChat ? body : `📩 ${pushName || jid}\n${body}` },
      { inResponseToIncoming: true, quoted: quotedMsg }
    );
    console.log(`Transcription envoyée (${text.length} car.)`);
  } catch (err) {
    console.error("Transcription vocal :", err.message);
    const errText = "🎙️ Impossible de transcrire ce vocal.";
    const targetJid =
      config.transcribeReplyInChat || !config.ownerNumber
        ? jid
        : `${config.ownerNumber}@s.whatsapp.net`;
    await sendChatReply(sock, targetJid, { text: errText }, {
      inResponseToIncoming: true,
      quoted: quotedMsg,
    }).catch(() => {});
  } finally {
    await sock.sendPresenceUpdate("paused", jid).catch(() => {});
  }
}

async function onMessage(sock, msg, type = "notify") {
  if (!msg?.message) return;
  if (isEmptyContent(msg)) return;

  const jid = msg.key.remoteJid;
  if (!jid) return;
  if (config.ignoreStatus && isStatusJid(jid)) return;
  if (jid.endsWith("@newsletter") || jid.endsWith("@broadcast")) return;

  const fromMe = Boolean(msg.key.fromMe);
  const audio = getAudioMessage(msg);
  const keys = messageTypeKeys(msg).join(",") || "?";
  console.log(
    `msg ${type} fromMe=${fromMe} audio=${Boolean(audio)} keys=${keys} ${msg.pushName || jid}`
  );

  if (alreadySeen(msg.key?.id)) return;
  if (!isRecentMessage(msg)) return;
  if (config.ignoreGroups && isGroupJid(jid)) return;
  if (!isGroupJid(jid)) noteChatJid(jid);

  const text = getMessageText(msg).trim();

  if (text.startsWith(config.prefix)) {
    const cmd = text.slice(config.prefix.length).trim().split(/\s+/)[0]?.toLowerCase();
    if ((cmd === "transcrire" || cmd === "vocal") && (isOwner(jid) || fromMe)) {
      const quotedDownload = buildQuotedDownloadMessage(msg, jid);
      if (quotedDownload) {
        await transcribeVoice(sock, quotedDownload, jid, quotedDownload.message.audioMessage, {
          quotedMsg: msg,
        });
        return;
      }
      if (audio && !fromMe) {
        await transcribeVoice(sock, msg, jid, audio);
        return;
      }
      await sendChatReply(sock, jid, {
        text: `Réponds à un vocal avec *${config.prefix}transcrire* pour obtenir le texte.`,
      }, { inResponseToIncoming: true });
      return;
    }
  }

  if (audio && !fromMe && shouldAutoTranscribe(jid)) {
    await transcribeVoice(sock, msg, jid, audio);
    return;
  }

  if (!text) return;

  if (fromMe && !text.startsWith(config.prefix)) return;

  const pushName = msg.pushName || "";
  console.log(`[${fromMe ? "moi" : pushName || jid}] ${text}`);

  if (!fromMe && shouldMarkIncomingAsRead(jid)) {
    await sock.readMessages([msg.key]);
  }

  if (!fromMe && config.showTyping) {
    await sock.sendPresenceUpdate("composing", jid);
  }

  const handled = await handleCommand({ sock, jid, text, pushName, fromMe });
  if (handled) {
    if (!fromMe && config.showTyping) await sock.sendPresenceUpdate("paused", jid);
    return;
  }

  if (fromMe) return;

  const auto = config.autoRepliesEnabled ? matchAutoReply(text) : null;
  if (auto) {
    await sendChatReply(sock, jid, { text: auto }, { inResponseToIncoming: true });
  }

  if (config.showTyping) {
    await sock.sendPresenceUpdate("paused", jid);
  }
}

writeHeartbeat("starting");
startBot().catch((err) => {
  console.error("Impossible de démarrer le bot :", err);
  process.exit(1);
});
