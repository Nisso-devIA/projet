import { NextRequest, NextResponse } from "next/server";
import { ADMIN_COOKIE, isValidSessionToken } from "@/lib/admin-session";
import { adminPath } from "@/lib/admin-paths";
import { getSessionStamp } from "@/lib/admin-store";

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === adminPath("/login")) {
    return NextResponse.next();
  }

  let stamp: string | undefined;
  try {
    stamp = await getSessionStamp();
  } catch {
    stamp = undefined;
  }

  const valid = await isValidSessionToken(
    request.cookies.get(ADMIN_COOKIE)?.value,
    stamp,
  );
  if (valid) return NextResponse.next();

  const login = request.nextUrl.clone();
  login.pathname = adminPath("/login");
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/dojo-admin", "/dojo-admin/:path*"],
};
