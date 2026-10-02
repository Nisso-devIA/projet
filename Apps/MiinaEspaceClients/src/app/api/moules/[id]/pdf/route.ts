import { NextResponse } from "next/server";
import fs from "fs/promises";
import { getMoule, mergedPdfPath, mouleHasMergedPdf } from "@/lib/store";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const moule = await getMoule(id);
  if (!moule || !mouleHasMergedPdf(moule)) {
    return NextResponse.json({ error: "PDF introuvable" }, { status: 404 });
  }

  try {
    const bytes = await fs.readFile(mergedPdfPath(id));
    return new NextResponse(bytes, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename="${id}.pdf"`,
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch {
    return NextResponse.json({ error: "Fichier manquant" }, { status: 404 });
  }
}
