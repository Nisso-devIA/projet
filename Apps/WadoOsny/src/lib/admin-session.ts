const COOKIE = "admin_session";
const encoder = new TextEncoder();

function isProduction() {
  return process.env.NODE_ENV === "production";
}

export const ADMIN_MAX_AGE = isProduction()
  ? 60 * 60 * 12
  : 60 * 60 * 24 * 7;

function secret() {
  const dedicated = process.env.ADMIN_SECRET?.trim();
  if (dedicated) return dedicated;
  if (isProduction()) return "";
  return process.env.ADMIN_PASSWORD?.trim() || "";
}

export function sessionSecretReady() {
  const value = secret();
  return isProduction() ? value.length >= 32 : value.length >= 8;
}

async function hmacHex(message: string) {
  const keyBytes = secret();
  if (!keyBytes) {
    throw new Error("ADMIN_SECRET manquant.");
  }
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(keyBytes),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return [...new Uint8Array(sig)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function safeEqual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i += 1) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export async function createSessionToken(stamp: string) {
  const exp = String(Date.now() + ADMIN_MAX_AGE * 1000);
  const payload = `${exp}.${stamp}`;
  return `${payload}.${await hmacHex(payload)}`;
}

export async function isValidSessionToken(
  token: string | undefined,
  expectedStamp?: string,
) {
  if (!token || !sessionSecretReady()) return false;
  const [exp, stamp, sig] = token.split(".");
  if (!exp || !stamp || !sig || Number(exp) < Date.now()) return false;
  if (expectedStamp && !safeEqual(stamp, expectedStamp)) return false;
  try {
    return safeEqual(sig, await hmacHex(`${exp}.${stamp}`));
  } catch {
    return false;
  }
}

export const ADMIN_COOKIE = COOKIE;
