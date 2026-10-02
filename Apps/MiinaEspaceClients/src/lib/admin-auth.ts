import {
  createHash,
  randomBytes,
  randomInt,
  scryptSync,
  timingSafeEqual,
} from "crypto";
import fs from "fs/promises";
import path from "path";
import {
  ADMIN_PASSWORD_MAX_AGE_DAYS,
  adminPassword,
} from "@/lib/auth";
import {
  adminAlertEmail,
  adminChangePasswordUrl,
  mailFrom,
  mailReplyTo,
  sendResend,
} from "@/lib/mail";
import { getDataDir } from "@/lib/store";

export {
  ADMIN_MUST_CHANGE_COOKIE,
  ADMIN_PASSWORD_MAX_AGE_DAYS,
} from "@/lib/auth";

export const ADMIN_PASSWORD_MAX_AGE_MS =
  ADMIN_PASSWORD_MAX_AGE_DAYS * 24 * 60 * 60 * 1000;

export const PASSWORD_CHANGE_CODE_TTL_MS = 15 * 60 * 1000;

export type AdminAuthState = {
  /** scrypt hash hex */
  passwordHash: string;
  salt: string;
  updatedAt: string;
  /** true tant que le mot de passe initial (env) n’a pas été remplacé */
  mustChangePassword: boolean;
  /** updatedAt pour lequel l’alerte J-7 a déjà été envoyée */
  expiryNotice7dFor?: string | null;
  /** updatedAt pour lequel l’alerte J-2 a déjà été envoyée */
  expiryNotice2dFor?: string | null;
};

type PasswordChangeChallenge = {
  codeHash: string;
  expiresAt: string;
  pendingHash: string;
  pendingSalt: string;
};

function authPath() {
  return path.join(getDataDir(), "admin-auth.json");
}

function challengePath() {
  return path.join(getDataDir(), "admin-pwd-challenge.json");
}

function hashAdminCode(code: string) {
  return createHash("sha256").update(code.trim()).digest("hex");
}

function adminCodeMatches(code: string, hash: string) {
  const actual = Buffer.from(hashAdminCode(code), "hex");
  const expected = Buffer.from(hash, "hex");
  if (actual.length !== expected.length) return false;
  return timingSafeEqual(actual, expected);
}

function generateNumericCode(length = 6) {
  const max = 10 ** length;
  return String(randomInt(0, max)).padStart(length, "0");
}

function maskEmail(to: string) {
  const at = to.indexOf("@");
  if (at <= 1) return to;
  return `${to.slice(0, 2)}•••${to.slice(at)}`;
}

async function readChallenge(): Promise<PasswordChangeChallenge | null> {
  try {
    const raw = await fs.readFile(challengePath(), "utf8");
    const parsed = JSON.parse(raw) as PasswordChangeChallenge;
    if (
      !parsed.codeHash ||
      !parsed.expiresAt ||
      !parsed.pendingHash ||
      !parsed.pendingSalt
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

async function writeChallenge(challenge: PasswordChangeChallenge) {
  await fs.mkdir(getDataDir(), { recursive: true });
  await fs.writeFile(
    challengePath(),
    `${JSON.stringify(challenge, null, 2)}\n`,
    "utf8",
  );
}

async function clearChallengeFile() {
  try {
    await fs.unlink(challengePath());
  } catch {
    /* ignore */
  }
}

function hashPassword(password: string, saltHex: string) {
  const salt = Buffer.from(saltHex, "hex");
  return scryptSync(password, salt, 64).toString("hex");
}

function hashesEqual(aHex: string, bHex: string) {
  const a = Buffer.from(aHex, "hex");
  const b = Buffer.from(bHex, "hex");
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export async function readAdminAuth(): Promise<AdminAuthState | null> {
  try {
    const raw = await fs.readFile(authPath(), "utf8");
    const parsed = JSON.parse(raw) as AdminAuthState;
    if (!parsed.passwordHash || !parsed.salt || !parsed.updatedAt) return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function writeAdminAuth(state: AdminAuthState) {
  await fs.mkdir(getDataDir(), { recursive: true });
  await fs.writeFile(authPath(), JSON.stringify(state, null, 2), "utf8");
}

export function isPasswordExpired(updatedAt: string) {
  const t = Date.parse(updatedAt);
  if (!Number.isFinite(t)) return true;
  return Date.now() - t >= ADMIN_PASSWORD_MAX_AGE_MS;
}

export function passwordExpiresAt(updatedAt: string) {
  const t = Date.parse(updatedAt);
  if (!Number.isFinite(t)) return null;
  return new Date(t + ADMIN_PASSWORD_MAX_AGE_MS);
}

/** Jours restants avant expiration (peut être négatif si déjà expiré). */
export function daysUntilPasswordExpiry(updatedAt: string) {
  const exp = passwordExpiresAt(updatedAt);
  if (!exp) return -Infinity;
  return (exp.getTime() - Date.now()) / (24 * 60 * 60 * 1000);
}

export function passwordNeedsChange(state: AdminAuthState | null) {
  if (!state) return true;
  if (state.mustChangePassword) return true;
  return isPasswordExpired(state.updatedAt);
}

export async function verifyAdminPassword(input: string) {
  const password = input.trim();
  if (!password) return { ok: false as const, mustChange: false };

  const state = await readAdminAuth();
  if (!state) {
    const envOk = timingSafeEqualStr(password, adminPassword());
    return { ok: envOk, mustChange: true, bootstrapping: true as const };
  }

  const candidate = hashPassword(password, state.salt);
  const ok = hashesEqual(candidate, state.passwordHash);
  if (!ok) return { ok: false as const, mustChange: false };
  return {
    ok: true as const,
    mustChange: passwordNeedsChange(state),
    bootstrapping: false as const,
  };
}

function timingSafeEqualStr(a: string, b: string) {
  const aBuf = Buffer.from(a);
  const bBuf = Buffer.from(b);
  if (aBuf.length !== bBuf.length) return false;
  return timingSafeEqual(aBuf, bBuf);
}

export function validateNewPassword(password: string) {
  if (password.length < 10) {
    return "Le mot de passe doit contenir au moins 10 caractères.";
  }
  if (password.length > 128) {
    return "Mot de passe trop long.";
  }
  return null;
}

export async function setAdminPassword(newPassword: string) {
  const err = validateNewPassword(newPassword);
  if (err) throw new Error(err);
  const salt = randomBytes(16).toString("hex");
  const passwordHash = hashPassword(newPassword, salt);
  const state: AdminAuthState = {
    passwordHash,
    salt,
    updatedAt: new Date().toISOString(),
    mustChangePassword: false,
    expiryNotice7dFor: null,
    expiryNotice2dFor: null,
  };
  await writeAdminAuth(state);
  return state;
}

export async function getAdminPasswordMeta() {
  const state = await readAdminAuth();
  const updatedAt = state?.updatedAt ?? null;
  const daysLeft =
    updatedAt != null ? daysUntilPasswordExpiry(updatedAt) : null;
  const hoursLeft = daysLeft != null ? daysLeft * 24 : null;
  const expiresAt =
    updatedAt != null ? passwordExpiresAt(updatedAt)?.toISOString() ?? null : null;

  return {
    mustChange: passwordNeedsChange(state),
    updatedAt,
    expiresAt,
    daysLeft,
    hoursLeft,
    /** Popup admin dans les 48 h avant expiration */
    warnWithin48h:
      hoursLeft != null && hoursLeft > 0 && hoursLeft <= 48 && Boolean(state),
    maxAgeDays: ADMIN_PASSWORD_MAX_AGE_DAYS,
    bootstrapped: Boolean(state),
  };
}

/** Marque mustChange si déjà expiré (cron). */
export async function markAdminPasswordExpiredIfNeeded() {
  const state = await readAdminAuth();
  if (!state) return null;
  if (isPasswordExpired(state.updatedAt) && !state.mustChangePassword) {
    state.mustChangePassword = true;
    await writeAdminAuth(state);
  }
  return state;
}

/** Démarre le challenge OTP e-mail (code 6 chiffres, 15 min). */
export async function startPasswordChangeChallenge(newPassword: string) {
  const err = validateNewPassword(newPassword);
  if (err) throw new Error(err);

  const to = adminAlertEmail();
  if (!to) {
    throw new Error(
      "Aucune adresse ADMIN_ALERT_EMAIL (ou ORDER_NOTIFY_EMAIL) configurée.",
    );
  }

  const salt = randomBytes(16).toString("hex");
  const pendingHash = hashPassword(newPassword, salt);
  const code = generateNumericCode(6);

  await writeChallenge({
    codeHash: hashAdminCode(code),
    expiresAt: new Date(Date.now() + PASSWORD_CHANGE_CODE_TTL_MS).toISOString(),
    pendingHash,
    pendingSalt: salt,
  });

  const sent = await sendResend({
    from: mailFrom(),
    reply_to: mailReplyTo(),
    to: [to],
    subject: "Code de confirmation — changement mot de passe admin Miina Recettes",
    text: [
      "Code de confirmation pour changer le mot de passe admin Miina Recettes Clients :",
      "",
      code,
      "",
      "Valable 15 minutes. Si vous n’êtes pas à l’origine de cette demande, ignorez ce message.",
    ].join("\n"),
  });

  if (!sent.ok) {
    await clearChallengeFile();
    throw new Error("Impossible d’envoyer le code par e-mail.");
  }

  return { to, maskedTo: maskEmail(to) };
}

export async function confirmPasswordChangeWithCode(code: string) {
  const challenge = await readChallenge();
  if (!challenge) {
    throw new Error("Aucun code en attente. Relancez la demande de changement.");
  }
  if (new Date(challenge.expiresAt).getTime() < Date.now()) {
    await clearChallengeFile();
    throw new Error("Code expiré. Demandez un nouveau code.");
  }
  if (!adminCodeMatches(code, challenge.codeHash)) {
    throw new Error("Code incorrect.");
  }

  const state: AdminAuthState = {
    passwordHash: challenge.pendingHash,
    salt: challenge.pendingSalt,
    updatedAt: new Date().toISOString(),
    mustChangePassword: false,
    expiryNotice7dFor: null,
    expiryNotice2dFor: null,
  };
  await writeAdminAuth(state);
  await clearChallengeFile();
  return state;
}

export async function clearPasswordChangeChallenge() {
  await clearChallengeFile();
}

/** Cron J-7 / J-2 + marque mustChange si expiré. */
export async function maybeSendPasswordExpiryEmails() {
  const state = await markAdminPasswordExpiredIfNeeded();
  if (!state?.updatedAt) {
    return { sent: [] as string[], skipped: "no_password" as const };
  }

  if (isPasswordExpired(state.updatedAt)) {
    return { sent: [] as string[], skipped: "expired" as const };
  }

  const to = adminAlertEmail();
  if (!to) {
    return { sent: [] as string[], skipped: "no_email" as const };
  }

  const daysLeft = daysUntilPasswordExpiry(state.updatedAt);
  const sent: string[] = [];
  const url = adminChangePasswordUrl();
  const when =
    daysLeft <= 2
      ? `dans environ ${Math.max(0, Math.ceil(daysLeft))} jour(s)`
      : `dans environ ${Math.ceil(daysLeft)} jours`;

  const html = `
    <p>Bonjour,</p>
    <p>Le mot de passe <strong>admin</strong> de Miina Recettes Clients expire ${when}
    (durée de validité : ${ADMIN_PASSWORD_MAX_AGE_DAYS} jours).</p>
    <p>Merci de le modifier dès que possible :</p>
    <p><a href="${url}">${url}</a></p>
    <p>Après expiration, un changement sera <strong>obligatoire</strong> à la prochaine connexion.</p>
    <p>— Miina Pâtisserie</p>
  `;

  let next = { ...state };

  if (daysLeft <= 2 && state.expiryNotice2dFor !== state.updatedAt) {
    const ok = await sendResend({
      from: mailFrom(),
      reply_to: mailReplyTo(),
      to: [to],
      subject: "[Miina] Mot de passe admin — expire dans 2 jours",
      html,
    });
    if (ok.ok) {
      next = { ...next, expiryNotice2dFor: state.updatedAt };
      sent.push("d2");
    }
  } else if (daysLeft <= 7 && state.expiryNotice7dFor !== state.updatedAt) {
    const ok = await sendResend({
      from: mailFrom(),
      reply_to: mailReplyTo(),
      to: [to],
      subject: "[Miina] Mot de passe admin — expire dans 7 jours",
      html,
    });
    if (ok.ok) {
      next = { ...next, expiryNotice7dFor: state.updatedAt };
      sent.push("d7");
    }
  }

  if (sent.length) {
    await writeAdminAuth(next);
  }

  return { sent, daysLeft: Number(daysLeft.toFixed(1)) };
}
