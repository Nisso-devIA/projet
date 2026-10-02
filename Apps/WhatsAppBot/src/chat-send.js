import { config, isOwner } from "./config.js";

function isOwnerJid(jid) {
  return isOwner(jid);
}

/**
 * Envoie un message dans une conversation (jamais en masse).
 * Par défaut : uniquement en réponse à un message reçu, ou vers le propriétaire.
 */
export async function sendChatReply(sock, jid, content, options = {}) {
  if (!jid || jid === "status@broadcast" || jid.endsWith("@broadcast")) {
    throw new Error("Envoi refusé : ce n'est pas une conversation privée/groupe");
  }

  const { inResponseToIncoming = false, allowProactive = false, ...sendOpts } = options;

  if (isOwnerJid(jid)) {
    return sock.sendMessage(jid, content, sendOpts);
  }

  if (allowProactive || config.allowProactiveChatMessages) {
    return sock.sendMessage(jid, content, sendOpts);
  }

  if (!inResponseToIncoming) {
    console.warn(`Envoi bloqué vers ${jid} — pas de message proactif vers les contacts`);
    return null;
  }

  return sock.sendMessage(jid, content, sendOpts);
}
