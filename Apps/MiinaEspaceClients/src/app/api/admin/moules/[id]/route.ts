import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";
import { removeMouleImageFiles } from "@/lib/moule-image";
import { prepareRecetteFlip } from "@/lib/prepare-recette";
import {
  isAllowedRecipeFile,
  recipeFileExt,
  titleFromRecipeFileName,
} from "@/lib/recipe-upload";
import {
  getDataDir,
  readCatalog,
  recettesDir,
  writeCatalog,
} from "@/lib/store";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  try {
    const body = (await request.json()) as {
      title?: string;
      fallbackHref?: string;
      image?: string;
    };
    const catalog = await readCatalog();
    const idx = catalog.moules.findIndex((m) => m.id === id);
    if (idx < 0) {
      return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
    }
    if (typeof body.title === "string" && body.title.trim()) {
      catalog.moules[idx].title = body.title.trim();
    }
    if (typeof body.fallbackHref === "string") {
      catalog.moules[idx].fallbackHref = body.fallbackHref.trim() || undefined;
    }
    if (typeof body.image === "string") {
      catalog.moules[idx].image = body.image.trim() || undefined;
    }
    await writeCatalog(catalog);
    return NextResponse.json(catalog.moules[idx]);
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }
}

export async function DELETE(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }
  catalog.moules.splice(idx, 1);
  await writeCatalog(catalog);

  const root = getDataDir();
  await fs.rm(recettesDir(id), { recursive: true, force: true });
  await fs.rm(path.join(root, "merged", `${id}.pdf`), { force: true });
  await fs.rm(path.join(root, "flip", id), { recursive: true, force: true });
  await removeMouleImageFiles(id);

  return NextResponse.json({ ok: true });
}

export async function POST(request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }

  const form = await request.formData();
  const files = form
    .getAll("file")
    .filter((f): f is File => f instanceof File && f.size > 0);

  if (files.length === 0) {
    return NextResponse.json({ error: "Fichier requis" }, { status: 400 });
  }

  const MAX_BYTES = 15 * 1024 * 1024;
  for (const file of files) {
    if (!isAllowedRecipeFile(file)) {
      return NextResponse.json(
        {
          error: `Format non supporté (${file.name}). PDF, PNG, JPG, WEBP, GIF ou TIFF.`,
        },
        { status: 400 },
      );
    }
    if (file.size > MAX_BYTES) {
      return NextResponse.json(
        { error: `Fichier trop lourd (${file.name}, max 15 Mo)` },
        { status: 400 },
      );
    }
  }

  const dir = recettesDir(id);
  await fs.mkdir(dir, { recursive: true });

  const added: { id: string; filename: string }[] = [];

  try {
    for (const file of files) {
      const recetteId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
      const ext = recipeFileExt(file) || ".bin";
      const safeBase = file.name
        .replace(/\.[^.]+$/, "")
        .replace(/[^a-zA-Z0-9._-]+/g, "_")
        .slice(0, 80);
      const filename = `${recetteId}-${safeBase || "recette"}${ext}`;
      const buffer = Buffer.from(await file.arrayBuffer());
      await fs.writeFile(path.join(dir, filename), buffer);

      const recette = {
        id: recetteId,
        filename,
        originalName: file.name,
        title: titleFromRecipeFileName(file.name),
        kind: "sucre" as const,
        addedAt: new Date().toISOString(),
        flipPageCount: 0,
        readyAt: null as string | null,
      };
      catalog.moules[idx].recettes.push(recette);
      added.push({ id: recetteId, filename });
      await writeCatalog(catalog);
      await prepareRecetteFlip(id, recetteId);
    }
  } catch (err) {
    for (const item of added) {
      const fresh = await readCatalog();
      const mIdx = fresh.moules.findIndex((m) => m.id === id);
      if (mIdx >= 0) {
        fresh.moules[mIdx].recettes = fresh.moules[mIdx].recettes.filter(
          (r) => r.id !== item.id,
        );
        await writeCatalog(fresh);
      }
      await fs.unlink(path.join(dir, item.filename)).catch(() => undefined);
    }
    const message = err instanceof Error ? err.message : "Préparation flip échouée";
    return NextResponse.json({ error: message }, { status: 500 });
  }

  const updated = await readCatalog();
  const moule = updated.moules.find((m) => m.id === id);
  return NextResponse.json(moule);
}
