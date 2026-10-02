/** Chemin public de l’espace admin (volontairement non évident). */
export const ADMIN_BASE_PATH = "/dojo-admin";

export function adminPath(suffix = "") {
  if (!suffix) return ADMIN_BASE_PATH;
  if (suffix.startsWith("?")) return `${ADMIN_BASE_PATH}${suffix}`;
  return `${ADMIN_BASE_PATH}${suffix.startsWith("/") ? suffix : `/${suffix}`}`;
}
