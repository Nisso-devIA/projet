import fs from "fs/promises";
import path from "path";
import sharp from "sharp";
import { convertSourceToFlip, isImageRecettePath, isPdfRecettePath } from "@/lib/flip-convert";
import { removeRecetteFlip } from "@/lib/flip-storage";
import { imageExtFromFile } from "@/lib/moule-image";
import { getDataDir, readCatalog, writeCatalog } from "@/lib/store";

export { imageExtFromFile };

/** IDs flipbook (réutilise data/flip/{moule}/{recette}/). */
export const ENTRETIEN_FLIP_MOULE = "entretien";
export const ENTRETIEN_FLIP_RECETTE = "guide";

const SOURCE_BASENAME = "source";

export function entretienSourceDir() {
  return path.join(getDataDir(), "entretien");
}

export async function findEntretienSourceFile() {
  const dir = entretienSourceDir();
  try {
    const entries = await fs.readdir(dir);
    const match = entries.find((name) => path.parse(name).name === SOURCE_BASENAME);
    return match ? path.join(dir, match) : null;
  } catch {
    return null;
  }
}

export async function removeEntretienSourceFiles() {
  const dir = entretienSourceDir();
  try {
    const entries = await fs.readdir(dir);
    await Promise.all(
      entries
        .filter((name) => path.parse(name).name === SOURCE_BASENAME)
        .map((name) => fs.unlink(path.join(dir, name)).catch(() => undefined)),
    );
  } catch {
    /* ignore */
  }
}

export async function clearEntretienFlip() {
  await removeRecetteFlip(ENTRETIEN_FLIP_MOULE, ENTRETIEN_FLIP_RECETTE);
  await removeEntretienSourceFiles();
  // Ancien stockage bannière
  try {
    const legacy = path.join(getDataDir(), "images", "entretien");
    await fs.rm(legacy, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}

export async function saveEntretienSource(
  buffer: Buffer,
  originalName: string,
  ext: string,
) {
  await fs.mkdir(entretienSourceDir(), { recursive: true });
  await removeEntretienSourceFiles();

  let outExt = ext === ".jpeg" ? ".jpg" : ext;
  let outBuf = buffer;

  if (outExt === ".tif" || outExt === ".tiff") {
    try {
      outBuf = await sharp(buffer).rotate().png().toBuffer();
      outExt = ".png";
    } catch {
      throw new Error(
        "Impossible de lire ce TIFF. Essayez PNG/JPG/PDF, ou un TIFF non compressé.",
      );
    }
  }

  const filename = `${SOURCE_BASENAME}${outExt}`;
  const full = path.join(entretienSourceDir(), filename);
  await fs.writeFile(full, outBuf);
  return { path: full, filename, originalName };
}

export async function prepareEntretienFlip() {
  const sourcePath = await findEntretienSourceFile();
  if (!sourcePath) {
    await removeRecetteFlip(ENTRETIEN_FLIP_MOULE, ENTRETIEN_FLIP_RECETTE);
    return 0;
  }
  if (!isPdfRecettePath(sourcePath) && !isImageRecettePath(sourcePath)) {
    throw new Error("Format non supporté (PDF ou image)");
  }
  return convertSourceToFlip(
    ENTRETIEN_FLIP_MOULE,
    ENTRETIEN_FLIP_RECETTE,
    sourcePath,
  );
}

export function entretienViewerHref(catalog: {
  entretienHref: string;
  entretienFlipPageCount?: number;
}) {
  if ((catalog.entretienFlipPageCount ?? 0) > 0) {
    return "/espace/entretien";
  }
  return catalog.entretienHref || "#";
}

export function entretienFlipReady(catalog: {
  entretienFlipPageCount?: number;
}) {
  return (catalog.entretienFlipPageCount ?? 0) > 0;
}

export async function syncEntretienCatalogMeta(pages: number, originalName?: string) {
  const catalog = await readCatalog();
  catalog.entretienFlipPageCount = pages;
  catalog.entretienReadyAt = pages > 0 ? new Date().toISOString() : null;
  if (originalName !== undefined) {
    catalog.entretienOriginalName = originalName || undefined;
  }
  // Plus utilisé comme bannière
  catalog.entretienImage = undefined;
  await writeCatalog(catalog);
  return catalog;
}
