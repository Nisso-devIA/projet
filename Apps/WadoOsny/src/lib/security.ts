import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

const WINDOW_MS = 20 * 60 * 1000;
const MAX_ATTEMPTS = 5;
const FILE = path.join(process.cwd(), "data", "login-attempts.json");

type Attempt = { count: number; resetAt: number };
type Store = Record<string, Attempt>;

let queue: Promise<unknown> = Promise.resolve();

function withLock<T>(fn: () => Promise<T>): Promise<T> {
  const run = queue.then(fn, fn);
  queue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

async function readStore(): Promise<Store> {
  try {
    const raw = await readFile(FILE, "utf8");
    const parsed = JSON.parse(raw) as Store;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

async function writeStore(store: Store) {
  await mkdir(path.dirname(FILE), { recursive: true });
  const tmp = `${FILE}.${process.pid}.tmp`;
  await writeFile(tmp, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tmp, FILE);
}

function prune(store: Store, now: number) {
  for (const [ip, entry] of Object.entries(store)) {
    if (!entry || entry.resetAt <= now) delete store[ip];
  }
}

export function isProduction() {
  return process.env.NODE_ENV === "production";
}

export function clientIpFromHeaders(headerList: Headers) {
  return (
    headerList.get("x-real-ip")?.trim() ||
    headerList.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "local"
  );
}

export async function consumeLoginAttempt(ip: string) {
  return withLock(async () => {
    const now = Date.now();
    const store = await readStore();
    prune(store, now);

    const current = store[ip];
    if (!current || current.resetAt <= now) {
      store[ip] = { count: 1, resetAt: now + WINDOW_MS };
      await writeStore(store);
      return { ok: true as const, remaining: MAX_ATTEMPTS - 1 };
    }
    if (current.count >= MAX_ATTEMPTS) {
      const minutes = Math.max(1, Math.ceil((current.resetAt - now) / 60000));
      return { ok: false as const, retryMinutes: minutes };
    }
    current.count += 1;
    store[ip] = current;
    await writeStore(store);
    return { ok: true as const, remaining: MAX_ATTEMPTS - current.count };
  });
}

export async function clearLoginAttempts(ip: string) {
  return withLock(async () => {
    const store = await readStore();
    if (!(ip in store)) return;
    delete store[ip];
    await writeStore(store);
  });
}

export function publicError(error: unknown, fallback: string) {
  if (!isProduction() && error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function sanitizeHref(raw: string, allowEmpty = false) {
  const value = raw.trim();
  if (!value) return allowEmpty ? "" : "";
  if (value.startsWith("/")) return value;
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return "";
    if (isProduction() && url.protocol === "http:") {
      url.protocol = "https:";
    }
    return url.toString();
  } catch {
    return "";
  }
}
