import { NextResponse } from "next/server";
import {
  ENTRETIEN_FLIP_MOULE,
  ENTRETIEN_FLIP_RECETTE,
  entretienFlipReady,
} from "@/lib/entretien";
import { readFlipPage } from "@/lib/flip-storage";
import { readCatalog } from "@/lib/store";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ page: string }> };

export async function GET(_request: Request, ctx: Ctx) {
  const { page: rawPage } = await ctx.params;
  const page = Math.floor(Number(rawPage));
  if (!Number.isFinite(page) || page < 1) {
    return NextResponse.json({ error: "Introuvable" }, { status: 404 });
  }

  const catalog = await readCatalog();
  if (
    !entretienFlipReady(catalog) ||
    page > (catalog.entretienFlipPageCount ?? 0)
  ) {
    return NextResponse.json({ error: "Introuvable" }, { status: 404 });
  }

  const pageData = await readFlipPage(
    ENTRETIEN_FLIP_MOULE,
    ENTRETIEN_FLIP_RECETTE,
    page,
  );
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
