import { NextResponse } from "next/server";
import {
  imageExtFromFile,
  removeMouleImageFiles,
  saveMouleImage,
} from "@/lib/moule-image";
import {
  mouleImagePublicPath,
  readCatalog,
  writeCatalog,
} from "@/lib/store";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

const MAX_BYTES = 5 * 1024 * 1024;

export async function POST(request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }

  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ error: "Image requise" }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { error: "Image trop lourde (max 5 Mo)" },
      { status: 400 },
    );
  }

  const ext = imageExtFromFile(file);
  if (!ext) {
    return NextResponse.json(
      { error: "Formats acceptés : PNG, JPG, WEBP, GIF, TIFF" },
      { status: 400 },
    );
  }

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    await saveMouleImage(id, buffer, ext);
    catalog.moules[idx].image = mouleImagePublicPath(id, Date.now());
    await writeCatalog(catalog);
    return NextResponse.json(catalog.moules[idx]);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upload impossible";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }

  await removeMouleImageFiles(id);
  catalog.moules[idx].image = undefined;
  await writeCatalog(catalog);
  return NextResponse.json(catalog.moules[idx]);
}
