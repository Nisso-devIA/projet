import { NextResponse } from "next/server";
import { readFlipPage } from "@/lib/flip-storage";
import { getRecette, recetteFlipReady } from "@/lib/store";

export const runtime = "nodejs";

type Ctx = {
  params: Promise<{ id: string; recetteId: string; page: string }>;
};

export async function GET(_request: Request, ctx: Ctx) {
  const { id, recetteId, page: rawPage } = await ctx.params;
  const page = Math.floor(Number(rawPage));
  if (!id || !recetteId || !Number.isFinite(page) || page < 1) {
    return NextResponse.json({ error: "Introuvable" }, { status: 404 });
  }

  const found = await getRecette(id, recetteId);
  if (
    !found ||
    !recetteFlipReady(found.recette) ||
    page > (found.recette.flipPageCount ?? 0)
  ) {
    return NextResponse.json({ error: "Introuvable" }, { status: 404 });
  }

  const pageData = await readFlipPage(id, recetteId, page);
  if (!pageData) {
    return NextResponse.json({ error: "Page manquante" }, { status: 404 });
  }

  return new NextResponse(new Uint8Array(pageData.bytes), {
    headers: {
      "Content-Type": pageData.contentType,
      "Cache-Control": "private, max-age=120",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
