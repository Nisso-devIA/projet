import { cookies } from "next/headers";
import {
  ADMIN_COOKIE,
  ADMIN_MAX_AGE,
  createSessionToken,
  isValidSessionToken,
} from "@/lib/admin-session";
import { ADMIN_BASE_PATH } from "@/lib/admin-paths";
import { getSessionStamp } from "@/lib/admin-store";

export { createSessionToken, isValidSessionToken, ADMIN_COOKIE };

const COOKIE_PATH = ADMIN_BASE_PATH;

function cookieSecure() {
  return process.env.NODE_ENV === "production";
}

export async function setAdminCookie(token: string) {
  const jar = await cookies();
  jar.set(ADMIN_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: COOKIE_PATH,
    maxAge: ADMIN_MAX_AGE,
    secure: cookieSecure(),
  });
}

export async function issueAdminSession() {
  const stamp = await getSessionStamp();
  await setAdminCookie(await createSessionToken(stamp));
}

export async function clearAdminCookie() {
  const jar = await cookies();
  jar.set(ADMIN_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    path: COOKIE_PATH,
    maxAge: 0,
    secure: cookieSecure(),
  });
}

export async function isAdminLoggedIn() {
  try {
    const jar = await cookies();
    const stamp = await getSessionStamp();
    return isValidSessionToken(jar.get(ADMIN_COOKIE)?.value, stamp);
  } catch {
    return false;
  }
}
