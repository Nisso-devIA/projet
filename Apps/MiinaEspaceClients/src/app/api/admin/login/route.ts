import { NextResponse } from "next/server";
import { ADMIN_COOKIE, ADMIN_MUST_CHANGE_COOKIE, signAdminSession } from "@/lib/auth";
import { verifyAdminPassword } from "@/lib/admin-auth";
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

  const ip = `admin:${clientIpFromHeaders(request.headers)}`;
  const limit = await consumeLoginAttempt(ip);
  if (!limit.ok) {
    return NextResponse.json(
      {
        error: `Trop de tentatives. Réessayez dans ${limit.retryMinutes} min.`,
      },
      { status: 429 },
    );
  }

  let password = "";
  try {
    const body = (await request.json()) as { password?: string };
    password = body.password?.trim() ?? "";
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  const result = await verifyAdminPassword(password);
  password = "";
  if (!result.ok) {
    return NextResponse.json({ error: "Mot de passe incorrect" }, { status: 401 });
  }

  await clearLoginAttempts(ip);

  const token = await signAdminSession();
  const response = NextResponse.json({
    ok: true,
    mustChange: result.mustChange,
  });
  response.cookies.set(ADMIN_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });

  if (result.mustChange) {
    response.cookies.set(ADMIN_MUST_CHANGE_COOKIE, "1", {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 2,
    });
  } else {
    response.cookies.set(ADMIN_MUST_CHANGE_COOKIE, "", {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 0,
    });
  }

  return response;
}
