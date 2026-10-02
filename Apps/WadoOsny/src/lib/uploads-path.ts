import path from "node:path";

/**
 * Dossier des uploads.
 * - Local (défaut) : public/uploads
 * - VPS : UPLOADS_DIR=/var/www/wado-osny/uploads
 */
export function getUploadsDir() {
  const custom = process.env.UPLOADS_DIR?.trim();
  if (custom) return path.resolve(custom);
  return path.join(process.cwd(), "public", "uploads");
}
