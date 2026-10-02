export function unwrapMessage(msg) {
  let m = msg?.message;
  if (!m) return null;

  const layers = [
    "ephemeralMessage",
    "viewOnceMessage",
    "viewOnceMessageV2",
    "viewOnceMessageV2Extension",
    "documentWithCaptionMessage",
    "deviceSentMessage",
    "editedMessage",
  ];

  for (let i = 0; i < 4 && m; i += 1) {
    const wrap = layers.find((key) => m[key]?.message);
    if (!wrap) break;
    m = m[wrap].message;
  }

  return m;
}

export function getAudioMessage(msg) {
  const m = unwrapMessage(msg);
  return m?.audioMessage || null;
}

export function getQuotedAudio(msg) {
  const m = unwrapMessage(msg);
  const quoted = m?.extendedTextMessage?.contextInfo?.quotedMessage;
  if (!quoted) return null;
  return quoted.audioMessage || null;
}

export function buildQuotedDownloadMessage(msg, jid) {
  const m = unwrapMessage(msg);
  const ctx = m?.extendedTextMessage?.contextInfo;
  const quoted = ctx?.quotedMessage;
  if (!quoted?.audioMessage) return null;
  return {
    key: {
      remoteJid: jid,
      id: ctx.stanzaId,
      fromMe: false,
      participant: ctx.participant,
    },
    message: quoted,
  };
}

export function getMessageText(msg) {
  const m = unwrapMessage(msg);
  if (!m) return "";

  if (m.conversation) return m.conversation;
  if (m.extendedTextMessage?.text) return m.extendedTextMessage.text;
  if (m.imageMessage?.caption) return m.imageMessage.caption;
  if (m.videoMessage?.caption) return m.videoMessage.caption;
  if (m.documentMessage?.caption) return m.documentMessage.caption;
  if (m.buttonsResponseMessage?.selectedButtonId) {
    return m.buttonsResponseMessage.selectedButtonId;
  }
  if (m.listResponseMessage?.singleSelectReply?.selectedRowId) {
    return m.listResponseMessage.singleSelectReply.selectedRowId;
  }
  if (m.templateButtonReplyMessage?.selectedId) {
    return m.templateButtonReplyMessage.selectedId;
  }
  return "";
}

export function isGroupJid(jid) {
  return String(jid || "").endsWith("@g.us");
}

export function isStatusJid(jid) {
  return jid === "status@broadcast";
}

export function displayPhone(jid) {
  return String(jid || "").split("@")[0].split(":")[0];
}

export function isRecentMessage(msg, maxAgeMs = 120_000) {
  const ts = Number(msg.messageTimestamp || 0) * 1000;
  if (!ts) return true;
  return Date.now() - ts <= maxAgeMs;
}

export function isEmptyContent(msg) {
  const m = unwrapMessage(msg);
  if (!m) return true;
  const keys = Object.keys(m).filter(
    (k) => k !== "messageContextInfo" && k !== "senderKeyDistributionMessage"
  );
  if (keys.length === 0) return true;
  return keys.every((k) => k === "protocolMessage");
}

export function messageTypeKeys(msg) {
  const m = unwrapMessage(msg);
  if (!m) return Object.keys(msg?.message || {});
  return Object.keys(m);
}
