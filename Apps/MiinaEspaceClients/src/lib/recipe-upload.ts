/** Extensions / MIME acceptés pour une recette (PDF ou image). */

const RECIPE_EXTS = new Set([
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".tif",
  ".tiff",
]);

const RECIPE_MIME = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
  "image/gif",
  "image/tiff",
  "image/tif",
]);

export function recipeFileExt(file: { name: string; type: string }) {
  const fromName = file.name.includes(".")
    ? `.${file.name.split(".").pop()!.toLowerCase()}`
    : "";
  if (RECIPE_EXTS.has(fromName)) {
    if (fromName === ".jpeg") return ".jpg";
    if (fromName === ".tiff") return ".tif";
    return fromName;
  }
  if (file.type === "application/pdf") return ".pdf";
  if (file.type === "image/png") return ".png";
  if (file.type === "image/webp") return ".webp";
  if (file.type === "image/gif") return ".gif";
  if (file.type === "image/jpeg" || file.type === "image/jpg") return ".jpg";
  if (file.type === "image/tiff" || file.type === "image/tif") return ".tif";
  return null;
}

export function isAllowedRecipeFile(file: { name: string; type: string }) {
  return Boolean(recipeFileExt(file) || RECIPE_MIME.has(file.type));
}

export function titleFromRecipeFileName(originalName: string) {
  return originalName
    .replace(/\.(pdf|png|jpe?g|webp|gif|tiff?)$/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim() || "Recette";
}
