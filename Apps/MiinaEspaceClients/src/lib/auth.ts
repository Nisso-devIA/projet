const encoder = new TextEncoder();

export const AUTH_COOKIE = "miina_espace_auth";
export const ADMIN_COOKIE = "miina_espace_admin";
/** Cookie flag : admin doit changer son mot de passe (middleware Edge-safe) */
export const ADMIN_MUST_CHANGE_COOKIE = "miina_espace_admin_must_change";
export const ADMIN_PASSWORD_MAX_AGE_DAYS = 90;

function secret() {
  const value = process.env.SITE_SECRET?.trim();
  if (!value || value.length < 16) {
    if (process.env.NODE_ENV !== "production") {
      return "miina-espace-clients-dev-secret-change-in-prod-32";
    }
    throw new Error("SITE_SECRET manquant.");
  }
  return value;
}

export function sitePassword() {
  let value = process.env.SITE_PASSWORD?.trim() || "recettes";
  // Retire guillemets éventuels du .env (SITE_PASSWORD="xxx")
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return value.trim();
}

export function adminPassword() {
  return process.env.ADMIN_PASSWORD?.trim() || "miina-admin";
}

function timingSafeEqualStr(a: string, b: string) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export function passwordsMatch(input: string) {
  return timingSafeEqualStr(input, sitePassword());
}

/** Préférer verifyAdminPassword (admin-auth) pour le flux admin. */
export function adminPasswordsMatch(input: string) {
  return timingSafeEqualStr(input, adminPassword());
}

async function hmacHex(message: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function signRole(role: "ok" | "admin") {
  const day = Math.floor(Date.now() / 86_400_000);
  const payload = `${role}:${day}`;
  return `${payload}.${await hmacHex(payload)}`;
}

async function verifyRole(
  token: string | undefined | null,
  role: "ok" | "admin",
) {
  if (!token) return false;
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return false;
  if (!timingSafeEqualStr(sig, await hmacHex(payload))) return false;
  const match = new RegExp(`^${role}:(\\d+)$`).exec(payload);
  if (!match) return false;
  const day = Math.floor(Date.now() / 86_400_000);
  const tokenDay = Number(match[1]);
  return tokenDay === day || tokenDay === day - 1;
}

export async function signSession() {
  return signRole("ok");
}

export async function verifySession(token: string | undefined | null) {
  return verifyRole(token, "ok");
}

export async function signAdminSession() {
  return signRole("admin");
}

export async function verifyAdminSession(token: string | undefined | null) {
  return verifyRole(token, "admin");
}
