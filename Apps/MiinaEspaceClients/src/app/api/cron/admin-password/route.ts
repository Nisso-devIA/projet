import { NextResponse } from "next/server";
import { maybeSendPasswordExpiryEmails } from "@/lib/admin-auth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function timingSafeEqualStr(a: string, b: string) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function cronSecretOk(request: Request) {
  const expected =
    process.env.CRON_SECRET?.trim() ||
    process.env.ADMIN_SECRET?.trim() ||
    process.env.SITE_SECRET?.trim() ||
    "";
  if (!expected) return false;
  const header = request.headers.get("authorization") || "";
  const bearer = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  const query = new URL(request.url).searchParams.get("secret") || "";
  return (
    (bearer.length > 0 && timingSafeEqualStr(bearer, expected)) ||
    (query.length > 0 && timingSafeEqualStr(query, expected))
  );
}

async function handle(request: Request) {
  if (!cronSecretOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const result = await maybeSendPasswordExpiryEmails();
    return NextResponse.json({ ok: true, ...result });
  } catch (error) {
    console.error("[cron/admin-password]", error);
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}

export async function GET(request: Request) {
  return handle(request);
}

export async function POST(request: Request) {
  return handle(request);
}
