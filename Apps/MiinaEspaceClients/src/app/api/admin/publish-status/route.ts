import { NextResponse } from "next/server";
import { canPublishToProd } from "@/lib/publish-moule";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({ canPublish: canPublishToProd() });
}
