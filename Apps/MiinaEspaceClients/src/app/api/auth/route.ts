import { NextResponse } from "next/server";
import { AUTH_COOKIE, passwordsMatch, signSession } from "@/lib/auth";
import {
  clearLoginAttempts,
  clientIpFromHeaders,
  consumeLoginAttempt,
  isTrustedPasswordOrigin,
  rejectedPasswordOrigin,
} from "@/lib/security";

export const runtime = "nodejs";

export async function POST(request: Request) {
  if (!isTrustedPasswordOrigin(request)) {
    return rejectedPasswordOrigin();
  }

  const ip = clientIpFromHeaders(request.headers);
  const limit = await consumeLoginAttempt(ip);
  if (!limit.ok) {
    return NextResponse.json(
      {
        ok: false,
        error: `Trop de tentatives. Réessayez dans ${limit.retryMinutes} min.`,
      },
      { status: 429 },
    );
  }

  let password = "";
  try {
    const body = (await request.json()) as { password?: string };
    password = String(body.password || "");
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  if (!passwordsMatch(password)) {
    password = "";
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  password = "";

  await clearLoginAttempts(ip);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(AUTH_COOKIE, await signSession(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}
