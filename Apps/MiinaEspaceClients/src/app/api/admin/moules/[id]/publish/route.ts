import { NextResponse } from "next/server";
import { canPublishToProd, publishMouleToProd } from "@/lib/publish-moule";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

export async function POST(_request: Request, ctx: Ctx) {
  if (!canPublishToProd()) {
    return NextResponse.json(
      { error: "Publication prod désactivée sur cette instance." },
      { status: 403 },
    );
  }

  const { id } = await ctx.params;
  try {
    const result = await publishMouleToProd(id);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Erreur";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
