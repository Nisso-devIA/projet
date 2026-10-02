import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "fs/promises";
import path from "path";
import { createCanvas } from "@napi-rs/canvas";
import {
  countFlipPages,
  FLIP_MAX_PAGES,
  flipPagesDir,
  removeRecetteFlip,
} from "@/lib/flip-storage";

const execFileAsync = promisify(execFile);
/** Rasterisation PDF haute fidélité (~600 DPI). */
const RENDER_SCALE = 8.3;
const PDFTOPPM_DPI = "600";

async function pdftoppmAvailable() {
  try {
    await execFileAsync("pdftoppm", ["-v"], { timeout: 8_000 });
    return true;
  } catch (error) {
    const err = error as {
      code?: string | number;
      stderr?: string | Buffer;
      message?: string;
    };
    if (err.code === "ENOENT") return false;
    const stderr = String(err.stderr || "");
    return /poppler|pdftoppm\s+version/i.test(stderr);
  }
}

async function convertWithPdftoppm(pdfPath: string, pagesDir: string) {
  const prefix = path.join(pagesDir, "raw");
  await execFileAsync(
    "pdftoppm",
    [
      "-png",
      "-r",
      PDFTOPPM_DPI,
      "-aa",
      "yes",
      "-aaVector",
      "yes",
      pdfPath,
      prefix,
    ],
    { timeout: 300_000, maxBuffer: 64 * 1024 * 1024 },
  );

  const files = (await fs.readdir(pagesDir))
    .filter((name) => /^raw-\d+\.png$/i.test(name))
    .sort((a, b) => {
      const na = Number(a.match(/(\d+)/)?.[1] || 0);
      const nb = Number(b.match(/(\d+)/)?.[1] || 0);
      return na - nb;
    });

  if (files.length < 1) throw new Error("Aucune page dans le PDF");
  if (files.length > FLIP_MAX_PAGES) {
    throw new Error(`PDF trop long (${FLIP_MAX_PAGES} pages max)`);
  }

  let pageCount = 0;
  for (const name of files) {
    pageCount += 1;
    const src = path.join(pagesDir, name);
    const dest = path.join(pagesDir, `${String(pageCount).padStart(3, "0")}.png`);
    await fs.rename(src, dest);
  }
  return pageCount;
}

/** pdf.js exige un constructeur (new CanvasFactory()), pas un objet littéral. */
class NodeCanvasFactory {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  create(width: number, height: number): { canvas: any; context: any } {
    const canvas = createCanvas(Math.ceil(width), Math.ceil(height));
    return { canvas, context: canvas.getContext("2d") };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  reset(canvasAndContext: { canvas: any }, width: number, height: number) {
    canvasAndContext.canvas.width = Math.ceil(width);
    canvasAndContext.canvas.height = Math.ceil(height);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  destroy(canvasAndContext: { canvas: any }) {
    canvasAndContext.canvas.width = 0;
    canvasAndContext.canvas.height = 0;
  }
}

async function convertWithPdfJs(pdfPath: string, pagesDir: string) {
  const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs");
  const data = new Uint8Array(await fs.readFile(pdfPath));
  const factory = new NodeCanvasFactory();

  const doc = await pdfjs.getDocument({
    data,
    useSystemFonts: true,
    CanvasFactory: NodeCanvasFactory,
  } as never).promise;

  try {
    if (doc.numPages < 1) throw new Error("Aucune page dans le PDF");
    if (doc.numPages > FLIP_MAX_PAGES) {
      throw new Error(`PDF trop long (${FLIP_MAX_PAGES} pages max)`);
    }

    for (let i = 1; i <= doc.numPages; i++) {
      const page = await doc.getPage(i);
      const viewport = page.getViewport({ scale: RENDER_SCALE });
      const canvasAndContext = factory.create(viewport.width, viewport.height);
      await page.render({
        canvasContext: canvasAndContext.context,
        viewport,
        canvas: canvasAndContext.canvas,
      } as never).promise;

      const png = canvasAndContext.canvas.toBuffer("image/png");
      await fs.writeFile(
        path.join(pagesDir, `${String(i).padStart(3, "0")}.png`),
        png,
      );
      factory.destroy(canvasAndContext);
    }

    return doc.numPages;
  } finally {
    doc.cleanup();
  }
}

/** Convertit un PDF unitaire en pages PNG pour le flipbook de la recette. */
export async function convertPdfToFlip(
  mouleId: string,
  recetteId: string,
  pdfPath: string,
) {
  try {
    await fs.access(pdfPath);
  } catch {
    await removeRecetteFlip(mouleId, recetteId);
    return 0;
  }

  await removeRecetteFlip(mouleId, recetteId);
  const pagesDir = flipPagesDir(mouleId, recetteId);
  await fs.mkdir(pagesDir, { recursive: true });

  try {
    let pageCount: number;
    if (await pdftoppmAvailable()) {
      try {
        pageCount = await convertWithPdftoppm(pdfPath, pagesDir);
      } catch (err) {
        const code = (err as { code?: string }).code;
        if (code === "ENOENT") {
          await fs.rm(pagesDir, { recursive: true, force: true });
          await fs.mkdir(pagesDir, { recursive: true });
          pageCount = await convertWithPdfJs(pdfPath, pagesDir);
        } else {
          throw err;
        }
      }
    } else {
      pageCount = await convertWithPdfJs(pdfPath, pagesDir);
    }

    const onDisk = await countFlipPages(mouleId, recetteId);
    if (onDisk !== pageCount) {
      throw new Error("Conversion flip incomplète");
    }
    return pageCount;
  } catch (error) {
    await removeRecetteFlip(mouleId, recetteId);
    throw error;
  }
}

const IMAGE_EXTS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".tif",
  ".tiff",
]);

export function isImageRecettePath(filePath: string) {
  return IMAGE_EXTS.has(path.extname(filePath).toLowerCase());
}

export function isPdfRecettePath(filePath: string) {
  return path.extname(filePath).toLowerCase() === ".pdf";
}

/** Image → flipbook : copie octet-à-octet si possible (aucune recompression). */
export async function convertImageToFlip(
  mouleId: string,
  recetteId: string,
  imagePath: string,
) {
  try {
    await fs.access(imagePath);
  } catch {
    await removeRecetteFlip(mouleId, recetteId);
    return 0;
  }

  await removeRecetteFlip(mouleId, recetteId);
  const pagesDir = flipPagesDir(mouleId, recetteId);
  await fs.mkdir(pagesDir, { recursive: true });

  const ext = path.extname(imagePath).toLowerCase();
  const copyAsIs = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);

  try {
    // Formats web : copie exacte du fichier d’origine (1 page).
    if (copyAsIs.has(ext)) {
      const outExt = ext === ".jpeg" ? ".jpg" : ext;
      await fs.copyFile(
        imagePath,
        path.join(pagesDir, `001${outExt}`),
      );
      const onDisk = await countFlipPages(mouleId, recetteId);
      if (onDisk !== 1) throw new Error("Conversion image incomplète");
      return 1;
    }

    // TIFF (éventuellement multipage) → PNG lossless pleine résolution, sans resize.
    const sharp = (await import("sharp")).default;
    const input = await fs.readFile(imagePath);
    const meta = await sharp(input, { failOn: "none" }).metadata();
    const pageCount = Math.min(
      Math.max(1, meta.pages || 1),
      FLIP_MAX_PAGES,
    );

    for (let i = 0; i < pageCount; i++) {
      const png = await sharp(input, {
        failOn: "none",
        page: i,
      })
        .rotate()
        .png({ compressionLevel: 9, effort: 10, palette: false })
        .toBuffer();
      await fs.writeFile(
        path.join(pagesDir, `${String(i + 1).padStart(3, "0")}.png`),
        png,
      );
    }

    const onDisk = await countFlipPages(mouleId, recetteId);
    if (onDisk !== pageCount) {
      throw new Error("Conversion image incomplète");
    }
    return pageCount;
  } catch (error) {
    await removeRecetteFlip(mouleId, recetteId);
    if (error instanceof Error && error.message.includes("Conversion")) {
      throw error;
    }
    throw new Error(
      "Impossible de lire cette image. Essayez PNG, JPG, WEBP, GIF ou TIFF.",
    );
  }
}

/** PDF ou image → flipbook. */
export async function convertSourceToFlip(
  mouleId: string,
  recetteId: string,
  sourcePath: string,
) {
  if (isPdfRecettePath(sourcePath)) {
    return convertPdfToFlip(mouleId, recetteId, sourcePath);
  }
  if (isImageRecettePath(sourcePath)) {
    return convertImageToFlip(mouleId, recetteId, sourcePath);
  }
  throw new Error("Format non supporté (PDF ou image)");
}
