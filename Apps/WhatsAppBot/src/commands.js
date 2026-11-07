import { config, isOwner } from "./config.js";
import { displayPhone, isGroupJid } from "./text.js";
import { formatLastReads } from "./read-receipts.js";
import { postTestStory } from "./status-post.js";
import { formatStatusViews } from "./status-views.js";
import { sendChatReply } from "./chat-send.js";

function helpText() {
  return [
    `*${config.botName}*`,
    "",
    "Commandes disponibles :",
    `• ${config.prefix}help — cette aide`,
    `• ${config.prefix}ping — tester le bot`,
    `• ${config.prefix}info — infos de la conversation`,
    `• ${config.prefix}heure — date et heure actuelles`,
    `• ${config.prefix}echo <texte> — répéter un message`,
    `• ${config.prefix}transcrire — transcrire un vocal (répondre au message)`,
    `• ${config.prefix}lectures — voir qui a lu tes messages (mode discret)`,
    `• ${config.prefix}story — tester une story WhatsApp`,
    `• ${config.prefix}vues — qui a ouvert le dernier statut`,
    "",
    "Conversations *stealth* : pas de bleu pour l'autre, mais alerte quand il lit tes messages.",
    "Stories live Twitch : vrai live seulement (titre sans offline) → story début/fin.",
    "Le bot ne contacte jamais tes contacts en message privé de sa propre initiative.",
    "Utilise *!transcrire* en réponse à un vocal.",
  ].join("\n");
}

const commands = {
  help: () => helpText(),
  aide: () => helpText(),
  menu: () => helpText(),
  start: () => helpText(),

  ping: () => "pong 🏓",

  heure: () => {
    const now = new Date();
    const formatted = new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "full",
      timeStyle: "medium",
      timeZone: "Europe/Paris",
    }).format(now);
    return `🕒 ${formatted}`;
  },

  info: ({ jid, pushName }) => {
    const lines = [
      `Nom : ${pushName || "inconnu"}`,
      `Numéro : ${displayPhone(jid)}`,
      `Type : ${isGroupJid(jid) ? "groupe" : "privé"}`,
      `Toi : ${isOwner(jid) ? "propriétaire" : "utilisateur"}`,
    ];
    return lines.join("\n");
  },

  echo: ({ args }) => {
    if (!args) return `Usage : ${config.prefix}echo <texte>`;
    return args;
  },

  lectures: ({ jid }) => {
    if (!isOwner(jid)) return "Réservé au propriétaire.";
    return formatLastReads();
  },
  lu: ({ jid }) => {
    if (!isOwner(jid)) return "Réservé au propriétaire.";
    return formatLastReads();
  },

  vues: ({ jid }) => {
    if (!isOwner(jid)) return "Réservé au propriétaire.";
    return formatStatusViews();
  },
  statut: ({ jid }) => {
    if (!isOwner(jid)) return "Réservé au propriétaire.";
    return formatStatusViews();
  },

  story: async ({ sock, jid, fromMe }) => {
    if (!isOwner(jid) && !fromMe) return "Réservé au propriétaire.";
    if (!config.liveAnnounce?.enabled) {
      return "Stories désactivées (liveAnnounce.enabled = false).";
    }
    try {
      const info = await postTestStory(sock);
      const lines = [
        "Story envoyée côté bot.",
        `Contacts audience : ${info.statusJidList.length}`,
        `Cache contacts : ${info.contactCount}`,
        `Statut WhatsApp : ${info.delivery}`,
      ];
      if (info.contactCount < 5) {
        lines.push(
          "⚠️ Peu de contacts synchronisés — laisse le bot connecté quelques minutes puis réessaie."
        );
      }
      if (info.delivery === "PENDING" || info.delivery === 0) {
        lines.push(
          "⚠️ Bug connu Baileys : la story peut rester invisible même si le bot dit OK."
        );
      }
      return lines.join("\n");
    } catch (err) {
      return `Échec story : ${err.message}`;
    }
  },
};

export async function handleCommand({ sock, jid, text, pushName, fromMe = false }) {
  const prefix = config.prefix;
  if (!text.startsWith(prefix)) return false;

  const body = text.slice(prefix.length).trim();
  if (!body) return false;

  const [rawName, ...rest] = body.split(/\s+/);
  const name = rawName.toLowerCase();
  const args = rest.join(" ").trim();
  const handler = commands[name];
  const ownerAccess = isOwner(jid) || fromMe;

  if (config.commandsOwnerOnly && !ownerAccess) {
    return false;
  }

  if (!handler) {
    await sendChatReply(sock, jid, {
      text: `Commande inconnue. Tape *${prefix}help* pour la liste.`,
    }, { inResponseToIncoming: true });
    return true;
  }

  const reply = await handler({ sock, jid, args, pushName, text, fromMe });
  if (reply) {
    await sendChatReply(sock, jid, { text: String(reply) }, { inResponseToIncoming: true });
  }
  return true;
}

export function matchAutoReply(text) {
  const lowered = text.toLowerCase();
  for (const rule of config.autoReplies || []) {
    const keywords = rule.keywords || [];
    const hit = keywords.some((kw) => lowered.includes(String(kw).toLowerCase()));
    if (hit && rule.reply) return rule.reply;
  }
  return null;
}
