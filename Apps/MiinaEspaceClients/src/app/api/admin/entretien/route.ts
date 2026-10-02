import { NextResponse } from "next/server";
import {
  clearEntretienFlip,
  imageExtFromFile,
  prepareEntretienFlip,
  saveEntretienSource,
  syncEntretienCatalogMeta,
} from "@/lib/entretien";
import { readCatalog, writeCatalog } from "@/lib/store";

export const runtime = "nodejs";

const MAX_BYTES = 40 * 1024 * 1024;
const IMAGE_EXTS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".tif",
  ".tiff",
]);

function sourceExtFromFile(file: File) {
  const nameExt = file.name.includes(".")
    ? `.${file.name.split(".").pop()!.toLowerCase()}`
    : "";
  if (nameExt === ".pdf" || file.type === "application/pdf") return ".pdf";
  const img = imageExtFromFile(file);
  if (img && IMAGE_EXTS.has(img)) return img;
  if (IMAGE_EXTS.has(nameExt)) {
    if (nameExt === ".jpeg") return ".jpg";
    if (nameExt === ".tiff") return ".tif";
    return nameExt;
  }
  return null;
}

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ error: "Fichier requis" }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { error: "Fichier trop lourd (max 40 Mo)" },
      { status: 400 },
    );
  }

  const ext = sourceExtFromFile(file);
  if (!ext) {
    return NextResponse.json(
      { error: "Formats acceptés : PDF, PNG, JPG, WEBP, GIF, TIFF" },
      { status: 400 },
    );
  }

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    await saveEntretienSource(buffer, file.name, ext);
    const pages = await prepareEntretienFlip();
    if (pages < 1) {
      throw new Error("Impossible de générer le feuilletage");
    }
    const catalog = await syncEntretienCatalogMeta(pages, file.name);
    return NextResponse.json({
      ok: true,
      entretienFlipPageCount: catalog.entretienFlipPageCount,
      entretienOriginalName: catalog.entretienOriginalName,
      entretienHref: catalog.entretienHref,
      entretienReadyAt: catalog.entretienReadyAt,
    });
  } catch (err) {
    await clearEntretienFlip().catch(() => undefined);
    await syncEntretienCatalogMeta(0, "").catch(() => undefined);
    const message = err instanceof Error ? err.message : "Upload impossible";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE() {
  await clearEntretienFlip();
  const catalog = await syncEntretienCatalogMeta(0, "");
  return NextResponse.json({
    ok: true,
    entretienFlipPageCount: 0,
    entretienOriginalName: null,
    entretienHref: catalog.entretienHref,
  });
}

export async function PATCH(request: Request) {
  let body: { entretienHref?: string };
  try {
    body = (await request.json()) as { entretienHref?: string };
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  const catalog = await readCatalog();
  if (typeof body.entretienHref === "string") {
    catalog.entretienHref = body.entretienHref.trim();
  }
  await writeCatalog(catalog);
  return NextResponse.json({
    ok: true,
    entretienHref: catalog.entretienHref,
    entretienFlipPageCount: catalog.entretienFlipPageCount ?? 0,
    entretienOriginalName: catalog.entretienOriginalName ?? null,
  });
}
