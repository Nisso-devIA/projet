import { NextResponse } from "next/server";
import fs from "fs/promises";
import {
  contentTypeForImagePath,
  findMouleImageFile,
} from "@/lib/moule-image";
import { getMoule } from "@/lib/store";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const moule = await getMoule(id);
  if (!moule) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }

  const filePath = await findMouleImageFile(id);
  if (!filePath) {
    return NextResponse.json({ error: "Image introuvable" }, { status: 404 });
  }

  try {
    const bytes = await fs.readFile(filePath);
    return new NextResponse(bytes, {
      headers: {
        "Content-Type": contentTypeForImagePath(filePath),
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch {
    return NextResponse.json({ error: "Fichier manquant" }, { status: 404 });
  }
}
