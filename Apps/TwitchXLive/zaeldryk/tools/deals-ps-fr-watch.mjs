#!/usr/bin/env node
/**
 * Deals PS FR — DualSense + cartes PSN (prix bas uniquement).
 * Indépendant de /opt/sentinelle.
 *
 * Env :
 *   DISCORD_BOT_TOKEN
 *   DISCORD_DEALS_PS_CHANNEL_ID
 *   JINA_API_KEY (whatsapp-bot/.env)
 *   STATE_FILE=/home/ubuntu/zaeldryk/state/deals-ps-fr.json
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36";

const TOKEN = (process.env.DISCORD_BOT_TOKEN || "").trim();
const CHANNEL_ID = (process.env.DISCORD_DEALS_PS_CHANNEL_ID || "").trim();
const JINA_API_KEY = (process.env.JINA_API_KEY || "").trim();
const STATE_FILE =
  process.env.STATE_FILE || "/home/ubuntu/zaeldryk/state/deals-ps-fr.json";

/** Search pages — aggregators cover FR merchants. */
const SEARCHES = [
  {
    category: "dualsense",
    label: "DualSense",
    urls: [
      "https://www.idealo.fr/cat/3015191I16-3015191/sony-manette-sans-fil-dualsense.html",
      "https://www.idealo.fr/preisvergleich/ProductCategory.html?q=DualSense",
      "https://ledenicheur.fr/search?q=dualsense",
    ],
  },
  {
    category: "psn",
    label: "Carte PSN",
    urls: [
      "https://www.idealo.fr/cat/19146I16-19146/playstation-store-cartes.html",
      "https://www.idealo.fr/preisvergleich/ProductCategory.html?q=carte+PSN",
      "https://ledenicheur.fr/search?q=carte+psn",
    ],
  },
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function jinaUrl(pageUrl) {
  const u = new URL(pageUrl);
  u.protocol = "http:";
  return `https://r.jina.ai/${u.toString()}`;
}

async function fetchViaJina(pageUrl) {
  let lastErr;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const headers = {
        "User-Agent": UA,
        Accept: "text/plain",
        "X-Respond-With": "markdown",
        "X-Timeout": "45",
      };
      if (JINA_API_KEY) headers.Authorization = `Bearer ${JINA_API_KEY}`;
      const response = await fetch(jinaUrl(pageUrl), {
        redirect: "follow",
        signal: AbortSignal.timeout(60_000),
        headers,
      });
      const body = await response.text();
      if (/Just a moment\.\.\./i.test(body) || /<!DOCTYPE html>/i.test(body)) {
        throw new Error(`Jina CF challenge HTTP ${response.status}`);
      }
      if (!response.ok) throw new Error(`Jina HTTP ${response.status}`);
      if (body.length < 400) throw new Error(`Jina body court (${body.length})`);
      return body;
    } catch (err) {
      lastErr = err;
      if (attempt < 3) await sleep(2000 * attempt);
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

function parsePriceToken(raw) {
  if (!raw) return null;
  let s = String(raw).replace(/\u00a0/g, " ").trim();
  // FR: 1.234,56 or 69,99 — EN: 69.99
  if (/^\d{1,3}(\.\d{3})+,\d{2}$/.test(s)) {
    s = s.replace(/\./g, "").replace(",", ".");
  } else if (/^\d+,\d{2}$/.test(s)) {
    s = s.replace(",", ".");
  }
  s = s.replace(/[^\d.]/g, "");
  const n = Number.parseFloat(s);
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.round(n * 100) / 100;
}

function extractEuroPrices(text) {
  const out = [];
  const re = /(\d{1,4}(?:[.,]\d{2})?)\s*€/gi;
  let m;
  while ((m = re.exec(text))) {
    const p = parsePriceToken(m[1]);
    if (p != null) out.push({ price: p, index: m.index });
  }
  return out;
}

function isAccessoryTitle(title) {
  return /coque|étui|etui|housse|chargeur|dock|station|câble|cable|grip|skin|stickers?|verre|protection|sacoche|support|batterie externe|thumb|capuchon/i.test(
    title,
  );
}

function isDualSenseTitle(title) {
  if (!/dual\s*-?\s*sense/i.test(title)) return false;
  if (isAccessoryTitle(title) && !/manette|controller|pad/i.test(title)) {
    return false;
  }
  return true;
}

function isPsnCardTitle(title) {
  if (/ps\s*plus|playstation\s*plus|abonnement|subscription/i.test(title)) {
    if (!/carte|card|wallet|cr[eé]dit|code|gift/i.test(title)) return false;
  }
  return (
    /(?:carte|card|wallet|cr[eé]dit|code|gift).{0,40}(?:psn|playstation\s*store|ps\s*store)/i.test(
      title,
    ) ||
    /(?:psn|playstation\s*store|ps\s*store).{0,40}(?:carte|card|wallet|cr[eé]dit|€|euros?)/i.test(
      title,
    ) ||
    /playstation\s*store.{0,20}\d+\s*€/i.test(title)
  );
}

function normalizeDualSenseModel(title) {
  const t = title.toLowerCase();
  if (/edge/.test(t)) return "DualSense Edge";
  if (/midnight\s*black|noir\s*midnight/.test(t)) return "DualSense Midnight Black";
  if (/cosmic\s*red|rouge\s*cosmic/.test(t)) return "DualSense Cosmic Red";
  if (/sterling\s*silver|argent/.test(t)) return "DualSense Sterling Silver";
  if (/galactic\s*purple|violet/.test(t)) return "DualSense Galactic Purple";
  if (/nova\s*pink|rose\s*nova/.test(t)) return "DualSense Nova Pink";
  if (/starlight\s*blue|bleu\s*starlight/.test(t)) return "DualSense Starlight Blue";
  if (/volcanic\s*red/.test(t)) return "DualSense Volcanic Red";
  if (/cobalt\s*blue/.test(t)) return "DualSense Cobalt Blue";
  if (/chroma|teal|ice|grey|gray|white|blanc|noir|black|ivoire|ivory/.test(t)) {
    const color =
      t.match(
        /(chroma\s*\w+|midnight black|cosmic red|sterling silver|galactic purple|nova pink|starlight blue|volcanic red|cobalt blue|blanc|white|noir|black|grey|gray|teal|ice)/i,
      )?.[1] || "Standard";
    return `DualSense ${color.replace(/\b\w/g, (c) => c.toUpperCase())}`;
  }
  return "DualSense Standard";
}

function normalizePsnAmount(title, price) {
  const m = title.match(/(\d{2,3})\s*€/);
  if (m) return `PSN ${m[1]}€`;
  const m2 = title.match(/(?:psn|store|carte|card|wallet)\D{0,12}(\d{2,3})(?:\s*€|\s*euros?)?/i);
  if (m2) return `PSN ${m2[1]}€`;
  // fallback: round price to common face values
  const faces = [10, 20, 25, 50, 70, 100];
  const nearest = faces.find((f) => Math.abs(f - price) < 3);
  if (nearest) return `PSN ${nearest}€`;
  return `PSN ~${Math.round(price)}€`;
}

function productKey(category, model) {
  return `${category}|${model.toLowerCase().replace(/\s+/g, " ").trim()}`;
}

function absUrl(href, base) {
  try {
    return new URL(href, base).toString();
  } catch {
    return href;
  }
}

/**
 * Parse markdown from Jina: look for markdown links + nearby prices.
 * Format often: [Title](url) ... 69,99 €
 */
function parseOffersFromMarkdown(md, category, pageUrl) {
  const offers = [];
  const linkRe = /\[([^\]]{8,180})\]\((https?:\/\/[^)\s]+)\)/g;
  let match;
  while ((match = linkRe.exec(md))) {
    const title = match[1].replace(/\s+/g, " ").trim();
    const url = match[2];
    const window = md.slice(match.index, match.index + 350);
    const prices = extractEuroPrices(window);
    if (!prices.length) continue;
    const price = prices[0].price;

    if (category === "dualsense") {
      if (!isDualSenseTitle(title)) continue;
      if (price < 35 || price > 280) continue; // accessories / kits outliers
      const model = normalizeDualSenseModel(title);
      offers.push({
        category,
        model,
        title,
        price,
        url: absUrl(url, pageUrl),
        merchant: guessMerchant(url, window),
        source: hostOf(pageUrl),
      });
    } else if (category === "psn") {
      if (!isPsnCardTitle(title) && !/\d+\s*€/.test(title)) continue;
      if (!isPsnCardTitle(title) && !/psn|playstation\s*store|ps\s*store/i.test(title)) {
        continue;
      }
      if (price < 5 || price > 120) continue;
      const model = normalizePsnAmount(title, price);
      const face = Number.parseInt(model.replace(/\D/g, ""), 10);
      if (face && price < face * 0.5) continue; // too good / scammy
      offers.push({
        category,
        model,
        title,
        price,
        url: absUrl(url, pageUrl),
        merchant: guessMerchant(url, window),
        source: hostOf(pageUrl),
      });
    }
  }
  return offers;
}

function hostOf(u) {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return "unknown";
  }
}

function guessMerchant(offerUrl, context) {
  const host = hostOf(offerUrl);
  if (!/idealo|ledenicheur|google|bing/i.test(host)) {
    return host;
  }
  const m = context.match(
    /(?:chez|marchand|vendeur|par)\s+([A-Za-z0-9][A-Za-z0-9.&'\- ]{1,40})/i,
  );
  if (m) return m[1].trim();
  // idealo often lists shop name near price
  const shop = context.match(
    /\n\s*([A-Z][A-Za-z0-9.&'\- ]{2,30})\s*\n[^\n]{0,40}\d+[.,]\d{2}\s*€/,
  );
  if (shop) return shop[1].trim();
  return host;
}

function pickBestPerModel(offers) {
  const map = new Map();
  for (const o of offers) {
    const key = productKey(o.category, o.model);
    const prev = map.get(key);
    if (!prev || o.price < prev.price) map.set(key, o);
  }
  return map;
}

async function sendDiscord(content, embeds) {
  if (!TOKEN || !CHANNEL_ID) {
    console.log("[discord] missing token/channel", content);
    return;
  }
  const payload = { content };
  if (embeds?.length) payload.embeds = embeds;
  const response = await fetch(
    `https://discord.com/api/v10/channels/${CHANNEL_ID}/messages`,
    {
      method: "POST",
      signal: AbortSignal.timeout(20_000),
      headers: {
        Authorization: `Bot ${TOKEN}`,
        "Content-Type": "application/json",
        "User-Agent": "ZaelDealsPS/1.0",
      },
      body: JSON.stringify(payload),
    },
  );
  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Discord HTTP ${response.status} ${body.slice(0, 200)}`);
  }
  console.log("[discord] ok", response.status);
}

async function loadState() {
  try {
    return JSON.parse(await readFile(STATE_FILE, "utf8"));
  } catch {
    return { best: {}, bootNotified: false };
  }
}

async function saveState(state) {
  await mkdir(dirname(STATE_FILE), { recursive: true });
  await writeFile(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

async function scanCategory(search) {
  const all = [];
  for (const url of search.urls) {
    try {
      console.log(`fetch ${search.category} ${url}`);
      const md = await fetchViaJina(url);
      const offers = parseOffersFromMarkdown(md, search.category, url);
      console.log(`  -> ${offers.length} offers`);
      all.push(...offers);
    } catch (err) {
      console.error(
        `  ERR ${url}:`,
        err instanceof Error ? err.message : err,
      );
    }
    await sleep(1500);
  }
  return all;
}

async function main() {
  if (!TOKEN || !CHANNEL_ID) {
    console.error("DISCORD_BOT_TOKEN / DISCORD_DEALS_PS_CHANNEL_ID requis");
    process.exit(1);
  }
  console.log(
    `deals-ps-fr — jina=${JINA_API_KEY ? "clé" : "anon"} — channel=${CHANNEL_ID}`,
  );

  const state = await loadState();
  if (!state.best) state.best = {};

  if (!state.bootNotified) {
    await sendDiscord(
      "🟢 Watcher **deals-ps** démarré.\nScan DualSense + cartes PSN (comparateurs FR). Alertes = **nouveau prix bas** uniquement.",
    );
    state.bootNotified = true;
    await saveState(state);
  }

  const collected = [];
  for (const search of SEARCHES) {
    const offers = await scanCategory(search);
    collected.push(...offers);
  }

  const bestNow = pickBestPerModel(collected);
  console.log(`models tracked this run: ${bestNow.size}`);

  const alerts = [];
  for (const [key, offer] of bestNow) {
    const prev = state.best[key];
    const isNew =
      !prev ||
      typeof prev.price !== "number" ||
      offer.price < prev.price - 0.009;
    if (isNew) {
      const oldPrice = prev?.price;
      state.best[key] = {
        category: offer.category,
        model: offer.model,
        price: offer.price,
        merchant: offer.merchant,
        url: offer.url,
        title: offer.title,
        source: offer.source,
        updated_at: new Date().toISOString(),
      };
      alerts.push({ offer, oldPrice });
    } else {
      // refresh metadata without alerting
      state.best[key] = {
        ...prev,
        merchant: offer.merchant,
        url: offer.url,
        title: offer.title,
        source: offer.source,
        checked_at: new Date().toISOString(),
      };
    }
  }

  state.lastRunAt = new Date().toISOString();
  state.lastOfferCount = collected.length;
  await saveState(state);

  // Cap alerts per run to avoid spam on first populate
  const isFirstPopulate =
    alerts.length > 8 &&
    alerts.filter((a) => a.oldPrice == null).length === alerts.length;
  const toSend = isFirstPopulate
    ? alerts
        .sort((a, b) => a.offer.price - b.offer.price)
        .slice(0, 12)
    : alerts;

  if (isFirstPopulate) {
    await sendDiscord(
      `📊 Premier inventaire : **${alerts.length}** références suivies. Top prix bas ci-dessous (max 12). Ensuite : alertes seulement si un prix descend.`,
    );
  }

  for (const { offer, oldPrice } of toSend) {
    const drop =
      oldPrice != null
        ? `\nAncien best : **${oldPrice.toFixed(2)} €** → **${offer.price.toFixed(2)} €**`
        : `\nPremier best connu : **${offer.price.toFixed(2)} €**`;
    await sendDiscord(`💸 **Nouveau prix bas** — ${offer.model}`, [
      {
        title: offer.model,
        description: [
          `**${offer.price.toFixed(2)} €** chez **${offer.merchant}**`,
          drop,
          `\n[${offer.title.slice(0, 120)}](${offer.url})`,
          `\n_source: ${offer.source}_`,
        ].join(""),
        url: offer.url,
        color: 0x00a651,
        footer: { text: "deals-ps-fr · new low only" },
        timestamp: new Date().toISOString(),
      },
    ]);
    await sleep(800);
  }

  console.log(`alerts sent: ${toSend.length}`);
}

await main();
