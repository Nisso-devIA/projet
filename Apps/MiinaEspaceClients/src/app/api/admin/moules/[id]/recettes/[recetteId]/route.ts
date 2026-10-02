import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";
import { removeRecetteFlip } from "@/lib/flip-storage";
import {
  parseRecetteKind,
  readCatalog,
  recettesDir,
  writeCatalog,
} from "@/lib/store";

type Ctx = { params: Promise<{ id: string; recetteId: string }> };

export async function PATCH(request: Request, ctx: Ctx) {
  const { id, recetteId } = await ctx.params;
  let title: string | undefined;
  let kindRaw: unknown;
  try {
    const body = (await request.json()) as { title?: string; kind?: string };
    if (typeof body.title === "string") title = body.title.trim();
    kindRaw = body.kind;
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  const kind = kindRaw !== undefined ? parseRecetteKind(kindRaw) : undefined;
  if (kindRaw !== undefined && !kind) {
    return NextResponse.json(
      { error: "Catégorie invalide (sucre ou sale)" },
      { status: 400 },
    );
  }
  if (title !== undefined) {
    if (!title) {
      return NextResponse.json({ error: "Titre requis" }, { status: 400 });
    }
    if (title.length > 120) {
      return NextResponse.json({ error: "Titre trop long" }, { status: 400 });
    }
  }
  if (title === undefined && kind === undefined) {
    return NextResponse.json({ error: "Rien à mettre à jour" }, { status: 400 });
  }

  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }
  const rIdx = catalog.moules[idx].recettes.findIndex((r) => r.id === recetteId);
  if (rIdx < 0) {
    return NextResponse.json({ error: "Recette introuvable" }, { status: 404 });
  }

  if (title !== undefined) {
    catalog.moules[idx].recettes[rIdx].title = title;
  }
  if (kind) {
    catalog.moules[idx].recettes[rIdx].kind = kind;
  }
  await writeCatalog(catalog);
  return NextResponse.json(catalog.moules[idx]);
}

export async function DELETE(_request: Request, ctx: Ctx) {
  const { id, recetteId } = await ctx.params;
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === id);
  if (idx < 0) {
    return NextResponse.json({ error: "Moule introuvable" }, { status: 404 });
  }
  const moule = catalog.moules[idx];
  const rIdx = moule.recettes.findIndex((r) => r.id === recetteId);
  if (rIdx < 0) {
    return NextResponse.json({ error: "Recette introuvable" }, { status: 404 });
  }
  const [removed] = moule.recettes.splice(rIdx, 1);
  await writeCatalog(catalog);
  await fs
    .unlink(path.join(recettesDir(id), removed.filename))
    .catch(() => undefined);
  await removeRecetteFlip(id, recetteId);

  const updated = await readCatalog();
  return NextResponse.json(updated.moules.find((m) => m.id === id));
}
