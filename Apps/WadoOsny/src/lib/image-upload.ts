import { mkdir, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { getUploadsDir } from "@/lib/uploads-path";

const MAX_BYTES = 5_000_000;

const KINDS = [
  {
    ext: "png",
    test: (bytes: Buffer) =>
      bytes.length > 8 &&
      bytes[0] === 0x89 &&
      bytes[1] === 0x50 &&
      bytes[2] === 0x4e &&
      bytes[3] === 0x47,
  },
  {
    ext: "jpg",
    test: (bytes: Buffer) =>
      bytes.length > 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff,
  },
  {
    ext: "webp",
    test: (bytes: Buffer) =>
      bytes.length > 12 &&
      bytes.toString("ascii", 0, 4) === "RIFF" &&
      bytes.toString("ascii", 8, 12) === "WEBP",
  },
] as const;

function sanitizeId(raw: string) {
  return raw.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "").slice(0, 48);
}

export async function saveImageUpload(
  file: File,
  folder: "gallery" | "instructors",
  preferredId?: string,
) {
  if (!file.size) throw new Error("Choisissez une image.");
  if (file.size > MAX_BYTES) throw new Error("Image trop lourde (5 Mo max).");
  const bytes = Buffer.from(await file.arrayBuffer());
  const kind = KINDS.find((entry) => entry.test(bytes));
  if (!kind) throw new Error("Utilisez un PNG, JPG ou WEBP.");

  const id =
    sanitizeId(preferredId || "") ||
    `${Date.now().toString(36)}-${randomBytes(4).toString("hex")}`;
  const dir = path.join(getUploadsDir(), folder);
  await mkdir(dir, { recursive: true });
  const name = `${id}.${kind.ext}`;
  await writeFile(path.join(/* turbopackIgnore: true */ dir, name), bytes);
  return `/uploads/${folder}/${name}?v=${Date.now()}`;
}

export async function removeUploadSrc(src: string) {
  const pathname = src.split("?")[0] ?? "";
  const match = pathname.match(/^\/uploads\/(gallery|instructors)\/([a-z0-9-]+\.(png|jpg|jpeg|webp))$/i);
  if (!match) return;
  const filePath = path.join(getUploadsDir(), match[1], match[2]);
  try {
    await unlink(filePath);
  } catch {
    /* ignore */
  }
}

export function isUploadSrc(src: string) {
  const pathname = src.split("?")[0] ?? "";
  return /^\/uploads\/(gallery|instructors)\/[a-z0-9-]+\.(png|jpg|jpeg|webp)$/i.test(
    pathname,
  );
}
