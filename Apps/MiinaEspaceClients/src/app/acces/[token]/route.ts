import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE, signSession } from "@/lib/auth";
import { consumeInviteToken, signPasswordReveal } from "@/lib/invites";
import {
  clientIpFromHeaders,
  consumeLoginAttempt,
} from "@/lib/security";

export const runtime = "nodejs";

/** Redirect sur le même host que la requête (évite 127.0.0.1 ↔ localhost). */
function sameHostUrl(request: NextRequest, path: string) {
  const host =
    request.headers.get("x-forwarded-host")?.split(",")[0]?.trim() ||
    request.headers.get("host")?.trim() ||
    "127.0.0.1:3003";
  const loopback =
    host.startsWith("127.") ||
    host.startsWith("localhost") ||
    host.startsWith("[::1]");
  const proto = loopback
    ? "http"
    : request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() ||
      "https";
  return new URL(path, `${proto}://${host}`);
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ token: string }> },
) {
  const { token: raw } = await context.params;
  const token = decodeURIComponent(raw || "").trim();

  const ip = `invite:${clientIpFromHeaders(request.headers)}`;
  const limit = await consumeLoginAttempt(ip);
  if (!limit.ok) {
    return NextResponse.redirect(
      sameHostUrl(request, "/acces/invalide?r=rate"),
    );
  }

  const result = await consumeInviteToken(token);
  if (!result.ok) {
    return NextResponse.redirect(
      sameHostUrl(request, `/acces/invalide?r=${result.reason}`),
    );
  }

  const { exp, sig } = signPasswordReveal();
  const dest = sameHostUrl(request, "/acces/bienvenue");
  dest.searchParams.set("e", String(exp));
  dest.searchParams.set("s", sig);

  const res = NextResponse.redirect(dest);
  res.cookies.set(AUTH_COOKIE, await signSession(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}
