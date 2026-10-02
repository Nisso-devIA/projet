import fs from "fs/promises";
import path from "path";
import sharp from "sharp";
import { mouleImagesDir } from "@/lib/store";

/** Formats stockés / servis au navigateur */
const STORED_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);

/** Formats acceptés à l’upload (TIFF converti en PNG) */
const INPUT_EXT = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".tif",
  ".tiff",
]);

export function imageExtFromFile(file: { name: string; type: string }) {
  const fromName = path.extname(file.name).toLowerCase();
  if (INPUT_EXT.has(fromName)) {
    if (fromName === ".jpeg") return ".jpg";
    if (fromName === ".tiff") return ".tif";
    return fromName;
  }
  if (file.type === "image/png") return ".png";
  if (file.type === "image/webp") return ".webp";
  if (file.type === "image/gif") return ".gif";
  if (file.type === "image/jpeg" || file.type === "image/jpg") return ".jpg";
  if (file.type === "image/tiff" || file.type === "image/tif") return ".tif";
  return null;
}

export async function findMouleImageFile(mouleId: string) {
  const dir = mouleImagesDir();
  try {
    const entries = await fs.readdir(dir);
    const match = entries.find((name) => {
      const base = path.parse(name).name;
      const ext = path.extname(name).toLowerCase();
      return base === mouleId && STORED_EXT.has(ext);
    });
    return match ? path.join(dir, match) : null;
  } catch {
    return null;
  }
}

export async function removeMouleImageFiles(mouleId: string) {
  const dir = mouleImagesDir();
  try {
    const entries = await fs.readdir(dir);
    await Promise.all(
      entries
        .filter((name) => path.parse(name).name === mouleId)
        .map((name) => fs.unlink(path.join(dir, name)).catch(() => undefined)),
    );
  } catch {
    /* ignore */
  }
}

export async function saveMouleImage(
  mouleId: string,
  buffer: Buffer,
  ext: string,
) {
  await fs.mkdir(mouleImagesDir(), { recursive: true });
  await removeMouleImageFiles(mouleId);

  let outExt = ext;
  let outBuf = buffer;

  if (ext === ".tif" || ext === ".tiff") {
    try {
      outBuf = await sharp(buffer).rotate().png().toBuffer();
      outExt = ".png";
    } catch {
      throw new Error(
        "Impossible de lire ce TIFF. Essayez un PNG/JPG, ou un TIFF non compressé.",
      );
    }
  }

  const filename = `${mouleId}${outExt}`;
  const full = path.join(mouleImagesDir(), filename);
  await fs.writeFile(full, outBuf);
  return full;
}

export function contentTypeForImagePath(filePath: string) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return "image/png";
  if (ext === ".webp") return "image/webp";
  if (ext === ".gif") return "image/gif";
  return "image/jpeg";
}
