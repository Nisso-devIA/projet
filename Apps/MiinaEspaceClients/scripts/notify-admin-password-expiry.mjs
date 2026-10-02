#!/usr/bin/env node
/**
 * Cron quotidien : alertes mail J-7 et J-2 avant expiration MDP admin (90 j),
 * et force mustChangePassword si déjà expiré.
 *
 * Env : DATA_DIR, RESEND_API_KEY, EMAIL_FROM,
 *       ADMIN_ALERT_EMAIL | ADMIN_NOTIFY_EMAIL | ORDER_NOTIFY_EMAIL
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const MAX_AGE_DAYS = 90;
const MAX_AGE_MS = MAX_AGE_DAYS * 24 * 60 * 60 * 1000;

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (!m) continue;
    if (process.env[m[1]] !== undefined) continue;
    let v = m[2];
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    process.env[m[1]] = v;
  }
}

const appRoot = path.resolve(__dirname, "..");
loadEnvFile(path.join(appRoot, ".env"));

const dataDir =
  process.env.DATA_DIR?.trim() || path.join(appRoot, "data");
const authPath = path.join(dataDir, "admin-auth.json");

function readAuth() {
  try {
    return JSON.parse(fs.readFileSync(authPath, "utf8"));
  } catch {
    return null;
  }
}

function writeAuth(state) {
  fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(authPath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

async function sendMail({ to, subject, html }) {
  const key = process.env.RESEND_API_KEY?.trim();
  const from =
    process.env.EMAIL_FROM?.trim() ||
    "Miina Pâtisserie <noreply@xn--miina-ptisserie-9jb.fr>";
  if (!key) throw new Error("RESEND_API_KEY manquant");
  if (!to) throw new Error("ADMIN_ALERT_EMAIL manquant");

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from, to: [to], subject, html }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Resend ${res.status}: ${body}`);
  }
}

function changeUrl() {
  return (
    process.env.ADMIN_CHANGE_PASSWORD_URL?.trim() ||
    "https://miinarecettesclients.xn--miina-ptisserie-9jb.fr/miina-admin/change-password"
  );
}

function mailHtml(daysLeft) {
  const when =
    daysLeft <= 2
      ? `dans environ ${Math.max(0, Math.ceil(daysLeft))} jour(s)`
      : `dans environ ${Math.ceil(daysLeft)} jours`;
  const url = changeUrl();
  return `
    <p>Bonjour,</p>
    <p>Le mot de passe <strong>admin</strong> de Miina Recettes Clients expire ${when}
    (durée de validité : ${MAX_AGE_DAYS} jours).</p>
    <p>Merci de le modifier dès que possible :</p>
    <p><a href="${url}">${url}</a></p>
    <p>Après expiration, un changement sera <strong>obligatoire</strong> à la prochaine connexion.</p>
    <p>— Miina Pâtisserie</p>
  `;
}

async function main() {
  const to =
    process.env.ADMIN_ALERT_EMAIL?.trim() ||
    process.env.ADMIN_NOTIFY_EMAIL?.trim() ||
    process.env.ORDER_NOTIFY_EMAIL?.trim();
  if (!to) {
    console.log("SKIP: ADMIN_ALERT_EMAIL / ORDER_NOTIFY_EMAIL non défini");
    process.exit(0);
  }

  const state = readAuth();
  if (!state?.updatedAt) {
    console.log("SKIP: pas encore de mot de passe admin défini (bootstrap)");
    process.exit(0);
  }

  const updatedAt = state.updatedAt;
  const expiresAt = Date.parse(updatedAt) + MAX_AGE_MS;
  const daysLeft = (expiresAt - Date.now()) / (24 * 60 * 60 * 1000);

  if (daysLeft <= 0) {
    if (!state.mustChangePassword) {
      state.mustChangePassword = true;
      writeAuth(state);
      console.log("EXPIRED: mustChangePassword=true");
    } else {
      console.log("EXPIRED: déjà marqué");
    }
    process.exit(0);
  }

  if (daysLeft <= 2 && state.expiryNotice2dFor !== updatedAt) {
    await sendMail({
      to,
      subject: "[Miina] Mot de passe admin — expire dans 2 jours",
      html: mailHtml(daysLeft),
    });
    state.expiryNotice2dFor = updatedAt;
    writeAuth(state);
    console.log("SENT: notice 2d");
    process.exit(0);
  }

  if (daysLeft <= 7 && state.expiryNotice7dFor !== updatedAt) {
    await sendMail({
      to,
      subject: "[Miina] Mot de passe admin — expire dans 7 jours",
      html: mailHtml(daysLeft),
    });
    state.expiryNotice7dFor = updatedAt;
    writeAuth(state);
    console.log("SENT: notice 7d");
    process.exit(0);
  }

  console.log(`OK: rien à envoyer (jours restants ≈ ${daysLeft.toFixed(1)})`);
}

main().catch((err) => {
  console.error("ERROR", err instanceof Error ? err.message : err);
  process.exit(1);
});
