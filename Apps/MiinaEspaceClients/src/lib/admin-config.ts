/** Admin désactivé sur la prod publique (ADMIN_ENABLED=0) — admin via test-prod uniquement. */
export function adminEnabled() {
  return process.env.ADMIN_ENABLED !== "0";
}

export function isAdminPath(pathname: string, adminBase = "/miina-admin") {
  return (
    pathname === "/admin" ||
    pathname.startsWith("/admin/") ||
    pathname.startsWith(adminBase) ||
    pathname.startsWith("/api/admin")
  );
}
