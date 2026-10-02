import fs from "fs/promises";
import path from "path";
import { convertSourceToFlip } from "@/lib/flip-convert";
import { removeRecetteFlip } from "@/lib/flip-storage";
import {
  getMoule,
  readCatalog,
  recettesDir,
  writeCatalog,
} from "@/lib/store";

/** Prépare le flipbook d’une recette (PDF ou image unitaire). */
export async function prepareRecetteFlip(mouleId: string, recetteId: string) {
  const moule = await getMoule(mouleId);
  if (!moule) throw new Error("Moule introuvable");

  const recette = moule.recettes.find((r) => r.id === recetteId);
  if (!recette) throw new Error("Recette introuvable");

  const sourcePath = path.join(recettesDir(mouleId), recette.filename);
  const flipPageCount = await convertSourceToFlip(mouleId, recetteId, sourcePath);

  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === mouleId);
  if (idx < 0) return flipPageCount;
  const rIdx = catalog.moules[idx].recettes.findIndex((r) => r.id === recetteId);
  if (rIdx < 0) return flipPageCount;

  catalog.moules[idx].recettes[rIdx] = {
    ...catalog.moules[idx].recettes[rIdx],
    flipPageCount,
    readyAt: flipPageCount > 0 ? new Date().toISOString() : null,
  };
  // Ancien champ moule (fusion) : plus utilisé
  catalog.moules[idx].mergedAt = null;
  catalog.moules[idx].flipPageCount = undefined;
  await writeCatalog(catalog);

  return flipPageCount;
}

export async function clearRecetteFlipMeta(mouleId: string, recetteId: string) {
  await removeRecetteFlip(mouleId, recetteId);
  const catalog = await readCatalog();
  const idx = catalog.moules.findIndex((m) => m.id === mouleId);
  if (idx < 0) return;
  const rIdx = catalog.moules[idx].recettes.findIndex((r) => r.id === recetteId);
  if (rIdx < 0) return;
  catalog.moules[idx].recettes[rIdx] = {
    ...catalog.moules[idx].recettes[rIdx],
    flipPageCount: 0,
    readyAt: null,
  };
  await writeCatalog(catalog);
}

/** Régénère les flipbooks de toutes les recettes d’un moule (migration). */
export async function prepareAllRecettesFlip(mouleId: string) {
  const moule = await getMoule(mouleId);
  if (!moule) throw new Error("Moule introuvable");
  const results: { id: string; pages: number }[] = [];
  for (const recette of moule.recettes) {
    const pages = await prepareRecetteFlip(mouleId, recette.id);
    results.push({ id: recette.id, pages });
  }
  return results;
}
