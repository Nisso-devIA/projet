import { createHash, createHmac, randomBytes, timingSafeEqual } from "crypto";
import { mkdir, readFile, rename, writeFile } from "fs/promises";
import path from "path";
import { getDataDir } from "@/lib/store";

const TOKEN_BYTES = 32;
const INVITE_TTL_MS = 14 * 24 * 60 * 60 * 1000;

function siteSecret() {
  const value = process.env.SITE_SECRET?.trim();
  if (value && value.length >= 16) return value;
  if (process.env.NODE_ENV !== "production") {
    return "miina-espace-clients-dev-secret-change-in-prod-32";
  }
  throw new Error("SITE_SECRET manquant.");
}

/** Jeton URL court pour afficher le MDP une fois après activation. */
export function signPasswordReveal(ttlMs = 5 * 60 * 1000) {
  const exp = Date.now() + ttlMs;
  const payload = `reveal:${exp}`;
  const sig = createHmac("sha256", siteSecret())
    .update(payload)
    .digest("base64url");
  return { exp, sig };
}

export function verifyPasswordReveal(expRaw: string, sigRaw: string) {
  const exp = Number(expRaw);
  if (!Number.isFinite(exp) || exp < Date.now()) return false;
  const payload = `reveal:${exp}`;
  const expected = createHmac("sha256", siteSecret())
    .update(payload)
    .digest("base64url");
  try {
    const a = Buffer.from(expected);
    const b = Buffer.from(String(sigRaw || ""));
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export type InviteRecord = {
  id: string;
  name: string;
  email: string;
  sentAt: string;
  tokenHash?: string;
  expiresAt?: string;
  usedAt?: string | null;
};

let queue: Promise<unknown> = Promise.resolve();

function invitesFile() {
  return path.join(getDataDir(), "invites.json");
}

function withLock<T>(fn: () => Promise<T>): Promise<T> {
  const run = queue.then(fn, fn);
  queue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

async function readAll(): Promise<InviteRecord[]> {
  try {
    const raw = await readFile(invitesFile(), "utf8");
    const parsed = JSON.parse(raw) as InviteRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function writeAll(invites: InviteRecord[]) {
  await mkdir(path.dirname(invitesFile()), { recursive: true });
  const tmp = `${invitesFile()}.${process.pid}.tmp`;
  await writeFile(tmp, `${JSON.stringify(invites, null, 2)}\n`, "utf8");
  await rename(tmp, invitesFile());
}

export function hashInviteToken(rawToken: string) {
  return createHash("sha256").update(rawToken, "utf8").digest("hex");
}

function newRawToken() {
  return randomBytes(TOKEN_BYTES).toString("base64url");
}

export async function listInvites(limit = 40) {
  const all = await readAll();
  return all.slice(-limit).reverse();
}

export async function recentInviteCount(windowMs: number) {
  const all = await readAll();
  const since = Date.now() - windowMs;
  return all.filter((item) => Date.parse(item.sentAt) >= since).length;
}

/** Crée l’invite + token one-time. Retourne le token brut (mail / logs une seule fois). */
export async function createInviteWithToken(name: string, email: string) {
  return withLock(async () => {
    const all = await readAll();
    const rawToken = newRawToken();
    const now = Date.now();
    const record: InviteRecord = {
      id: `${now.toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      name,
      email,
      sentAt: new Date(now).toISOString(),
      tokenHash: hashInviteToken(rawToken),
      expiresAt: new Date(now + INVITE_TTL_MS).toISOString(),
      usedAt: null,
    };
    all.push(record);
    await writeAll(all.slice(-500));
    return { record, rawToken };
  });
}

export async function revokeInviteById(id: string) {
  return withLock(async () => {
    const all = await readAll();
    const next = all.filter((item) => item.id !== id);
    if (next.length === all.length) return false;
    await writeAll(next);
    return true;
  });
}

export async function clearAllInvites() {
  return withLock(async () => {
    await writeAll([]);
  });
}

/** Liste sans secrets (pas de tokenHash). */
export async function listInvitesPublic(limit = 40) {
  const all = await listInvites(limit);
  return all.map(({ id, name, email, sentAt, expiresAt, usedAt }) => ({
    id,
    name,
    email,
    sentAt,
    expiresAt: expiresAt ?? null,
    usedAt: usedAt ?? null,
  }));
}

export type ConsumeInviteResult =
  | { ok: true; invite: InviteRecord }
  | { ok: false; reason: "invalid" | "used" | "expired" };

/** Cookie flash (legacy) — l’affichage MDP passe par ?e=&s= signés. */
export const INVITE_REVEAL_COOKIE = "miina_invite_reveal";

export async function consumeInviteToken(
  rawToken: string,
): Promise<ConsumeInviteResult> {
  const token = rawToken.trim();
  if (!token || token.length < 16 || token.length > 128) {
    return { ok: false, reason: "invalid" };
  }
  const expectedHash = hashInviteToken(token);

  return withLock(async () => {
    const all = await readAll();
    const idx = all.findIndex((item) => item.tokenHash === expectedHash);
    if (idx < 0) return { ok: false, reason: "invalid" };

    const invite = all[idx]!;
    if (invite.usedAt) return { ok: false, reason: "used" };
    if (invite.expiresAt && Date.parse(invite.expiresAt) <= Date.now()) {
      return { ok: false, reason: "expired" };
    }

    const updated: InviteRecord = {
      ...invite,
      usedAt: new Date().toISOString(),
    };
    all[idx] = updated;
    await writeAll(all);
    return { ok: true, invite: updated };
  });
}

/** Peek without consuming (for already-used / expired messaging). */
export async function peekInviteToken(
  rawToken: string,
): Promise<ConsumeInviteResult> {
  const token = rawToken.trim();
  if (!token || token.length < 16 || token.length > 128) {
    return { ok: false, reason: "invalid" };
  }
  const expectedHash = hashInviteToken(token);
  const all = await readAll();
  const invite = all.find((item) => item.tokenHash === expectedHash);
  if (!invite) return { ok: false, reason: "invalid" };
  if (invite.usedAt) return { ok: false, reason: "used" };
  if (invite.expiresAt && Date.parse(invite.expiresAt) <= Date.now()) {
    return { ok: false, reason: "expired" };
  }
  return { ok: true, invite };
}
