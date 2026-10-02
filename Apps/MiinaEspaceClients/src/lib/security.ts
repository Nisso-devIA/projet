import { mkdir, readFile, rename, writeFile } from "fs/promises";
import path from "path";
import { getDataDir } from "@/lib/store";

const WINDOW_MS = 20 * 60 * 1000;
const MAX_ATTEMPTS = process.env.NODE_ENV === "production" ? 5 : 50;

type Attempt = { count: number; resetAt: number };
type Store = Record<string, Attempt>;

let queue: Promise<unknown> = Promise.resolve();

function attemptsFile() {
  return path.join(getDataDir(), "login-attempts.json");
}

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
    const raw = await readFile(attemptsFile(), "utf8");
    const parsed = JSON.parse(raw) as Store;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

async function writeStore(store: Store) {
  await mkdir(path.dirname(attemptsFile()), { recursive: true });
  const tmp = `${attemptsFile()}.${process.pid}.tmp`;
  await writeFile(tmp, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tmp, attemptsFile());
}

function prune(store: Store, now: number) {
  for (const [ip, entry] of Object.entries(store)) {
    if (!entry || entry.resetAt <= now) delete store[ip];
  }
}

export function clientIpFromHeaders(headerList: Headers) {
  return (
    headerList.get("x-real-ip")?.trim() ||
    headerList.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "local"
  );
}

const PUBLIC_ORIGIN =
  "https://miinarecettesclients.xn--miina-ptisserie-9jb.fr";
const TEST_ORIGIN = "https://test-prod.xn--miina-ptisserie-9jb.fr";

/** Rejette les POST cross-site (exfiltration du mot de passe hors du site). */
export function isTrustedPasswordOrigin(request: Request) {
  const site = request.headers.get("sec-fetch-site");
  if (site === "cross-site") return false;

  const origin = request.headers.get("origin")?.trim();
  if (!origin) {
    // fetch same-origin envoie Origin ; absence = curl / health — OK si pas cross-site
    return true;
  }

  if (origin === PUBLIC_ORIGIN || origin === TEST_ORIGIN) return true;

  const xfHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const host = xfHost || request.headers.get("host")?.trim() || "";
  if (host) {
    if (origin === `https://${host}` || origin === `http://${host}`) return true;
  }

  if (process.env.NODE_ENV !== "production") {
    try {
      const { hostname } = new URL(origin);
      if (hostname === "localhost" || hostname === "127.0.0.1") return true;
    } catch {
      return false;
    }
  }

  return false;
}

export function rejectedPasswordOrigin() {
  return Response.json(
    { ok: false, error: "Origine non autorisée." },
    { status: 403 },
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

export function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export async function clearLoginAttempts(ip: string) {
  return withLock(async () => {
    const store = await readStore();
    if (!(ip in store)) return;
    delete store[ip];
    await writeStore(store);
  });
}
