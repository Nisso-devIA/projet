import fs from "fs/promises";
import path from "path";
import { getDataDir } from "@/lib/store";

export const FLIP_MAX_PAGES = 200;

const PAGE_FILE_RE = /^(\d{3})\.(png|jpe?g|webp|gif)$/i;

/** Flipbook d’une recette unitaire : data/flip/{mouleId}/{recetteId}/ */
export function flipDir(mouleId: string, recetteId: string) {
  return path.join(getDataDir(), "flip", mouleId, recetteId);
}

export function flipPagesDir(mouleId: string, recetteId: string) {
  return path.join(flipDir(mouleId, recetteId), "pages");
}

export function contentTypeForFlipPage(filePath: string) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return "image/png";
  if (ext === ".webp") return "image/webp";
  if (ext === ".gif") return "image/gif";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  return "application/octet-stream";
}

export async function findFlipPageFile(
  mouleId: string,
  recetteId: string,
  page: number,
) {
  const n = Math.floor(page);
  if (!Number.isFinite(n) || n < 1) return null;
  const prefix = String(n).padStart(3, "0");
  try {
    const entries = await fs.readdir(flipPagesDir(mouleId, recetteId));
    const match = entries.find((name) => {
      const m = PAGE_FILE_RE.exec(name);
      return m && m[1] === prefix;
    });
    return match ? path.join(flipPagesDir(mouleId, recetteId), match) : null;
  } catch {
    return null;
  }
}

export async function removeRecetteFlip(mouleId: string, recetteId: string) {
  await fs.rm(flipDir(mouleId, recetteId), { recursive: true, force: true });
}

/** Supprime tous les flipbooks d’un moule (y compris ancien layout plat). */
export async function removeMouleFlipBooks(mouleId: string) {
  await fs.rm(path.join(getDataDir(), "flip", mouleId), {
    recursive: true,
    force: true,
  });
}

export async function readFlipPage(
  mouleId: string,
  recetteId: string,
  page: number,
) {
  const filePath = await findFlipPageFile(mouleId, recetteId, page);
  if (!filePath) return null;
  try {
    const bytes = await fs.readFile(filePath);
    return {
      bytes,
      contentType: contentTypeForFlipPage(filePath),
      filePath,
    };
  } catch {
    return null;
  }
}

export async function countFlipPages(mouleId: string, recetteId: string) {
  try {
    const files = await fs.readdir(flipPagesDir(mouleId, recetteId));
    const nums = new Set<number>();
    for (const name of files) {
      const m = PAGE_FILE_RE.exec(name);
      if (m) nums.add(Number(m[1]));
    }
    return nums.size;
  } catch {
    return 0;
  }
}
