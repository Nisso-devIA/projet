import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { randomBytes, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import {
  PASSWORD_MAX_AGE_DAYS,
  PASSWORD_WARN_DAYS,
  passwordPolicyError,
} from "@/lib/admin-constants";
import { isProduction } from "@/lib/security";

export {
  PASSWORD_MAX_AGE_DAYS,
  PASSWORD_MIN_LENGTH,
  PASSWORD_WARN_DAYS,
} from "@/lib/admin-constants";

const scrypt = promisify(scryptCb);
const FILE = path.join(process.cwd(), "data", "admin.json");

export type AdminFile = {
  passwordHash: string;
  passwordChangedAt: string;
  sessionStamp: string;
};

export type PasswordStatus = {
  changedAt: string;
  expiresAt: string;
  daysLeft: number;
  expired: boolean;
  warning: boolean;
};

function newStamp() {
  return randomBytes(16).toString("hex");
}

async function hashPassword(password: string) {
  const salt = randomBytes(16);
  const key = (await scrypt(password, salt, 64)) as Buffer;
  return `${salt.toString("hex")}:${key.toString("hex")}`;
}

export async function verifyPassword(password: string, stored: string) {
  const [saltHex, keyHex] = stored.split(":");
  if (!saltHex || !keyHex) return false;
  const salt = Buffer.from(saltHex, "hex");
  const expected = Buffer.from(keyHex, "hex");
  const actual = (await scrypt(password, salt, 64)) as Buffer;
  if (actual.length !== expected.length) return false;
  return timingSafeEqual(actual, expected);
}

async function saveAdmin(data: AdminFile) {
  await mkdir(path.dirname(FILE), { recursive: true });
  await writeFile(FILE, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

async function bootstrapFromEnv(): Promise<AdminFile> {
  const initial = process.env.ADMIN_PASSWORD?.trim();
  if (!initial) {
    throw new Error(
      "Aucun mot de passe admin. Définissez ADMIN_PASSWORD dans .env pour le premier lancement, puis rechargez.",
    );
  }
  if (isProduction()) {
    const policy = passwordPolicyError(initial);
    if (policy) {
      throw new Error(`ADMIN_PASSWORD trop faible pour la production. ${policy}`);
    }
  }
  const data: AdminFile = {
    passwordHash: await hashPassword(initial),
    passwordChangedAt: new Date().toISOString(),
    sessionStamp: newStamp(),
  };
  await saveAdmin(data);
  return data;
}

export async function readAdmin(): Promise<AdminFile> {
  try {
    const raw = await readFile(FILE, "utf8");
    const parsed = JSON.parse(raw) as Partial<AdminFile>;
    if (parsed.passwordHash && parsed.passwordChangedAt) {
      if (parsed.sessionStamp) {
        return {
          passwordHash: parsed.passwordHash,
          passwordChangedAt: parsed.passwordChangedAt,
          sessionStamp: parsed.sessionStamp,
        };
      }
      const migrated: AdminFile = {
        passwordHash: parsed.passwordHash,
        passwordChangedAt: parsed.passwordChangedAt,
        sessionStamp: newStamp(),
      };
      await saveAdmin(migrated);
      return migrated;
    }
  } catch {
    /* first run */
  }
  return bootstrapFromEnv();
}

export async function getSessionStamp() {
  return (await readAdmin()).sessionStamp;
}

export async function getPasswordStatus(): Promise<PasswordStatus> {
  const { passwordChangedAt } = await readAdmin();
  const changed = new Date(passwordChangedAt).getTime();
  const expiresAtMs = changed + PASSWORD_MAX_AGE_DAYS * 24 * 60 * 60 * 1000;
  const daysLeft = Math.ceil((expiresAtMs - Date.now()) / (24 * 60 * 60 * 1000));
  return {
    changedAt: passwordChangedAt,
    expiresAt: new Date(expiresAtMs).toISOString(),
    daysLeft,
    expired: daysLeft <= 0,
    warning: daysLeft <= PASSWORD_WARN_DAYS,
  };
}

export async function isPasswordExpired() {
  return (await getPasswordStatus()).expired;
}

export async function passwordMatches(password: string) {
  const { passwordHash } = await readAdmin();
  return verifyPassword(password, passwordHash);
}

export async function updateAdminPassword(nextPassword: string) {
  const current = await readAdmin();
  await saveAdmin({
    ...current,
    passwordHash: await hashPassword(nextPassword),
    passwordChangedAt: new Date().toISOString(),
    sessionStamp: newStamp(),
  });
}

export function formatAdminDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "long",
  }).format(new Date(iso));
}
