import { NextResponse } from "next/server";
import { ADMIN_COOKIE, ADMIN_MUST_CHANGE_COOKIE } from "@/lib/auth";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  const clear = {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  };
  response.cookies.set(ADMIN_COOKIE, "", clear);
  response.cookies.set(ADMIN_MUST_CHANGE_COOKIE, "", clear);
  return response;
}
