import { existsSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { getUploadsDir } from "@/lib/uploads-path";

export const runtime = "nodejs";

const TYPES: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
};

export async function GET(
  _request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const parts = (await context.params).path ?? [];
  if (!parts.length || parts.some((p) => p.includes("..") || p.includes("\0"))) {
    return new Response("Not found", { status: 404 });
  }

  const root = path.resolve(getUploadsDir());
  const resolved = path.resolve(path.join(root, ...parts));
  if (!resolved.startsWith(root + path.sep)) {
    return new Response("Not found", { status: 404 });
  }
  if (!existsSync(resolved) || !statSync(resolved).isFile()) {
    return new Response("Not found", { status: 404 });
  }

  const ext = path.extname(resolved).toLowerCase();
  const type = TYPES[ext];
  if (!type) return new Response("Not found", { status: 404 });

  const body = await readFile(resolved);
  return new Response(body, {
    headers: {
      "Content-Type": type,
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
    },
  });
}
