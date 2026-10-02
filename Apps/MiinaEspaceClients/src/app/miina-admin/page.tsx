import { AdminDashboard } from "@/components/admin/AdminDashboard";
import { getAdminPasswordMeta } from "@/lib/admin-auth";
import { readCatalog } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const [catalog, passwordMeta] = await Promise.all([
    readCatalog(),
    getAdminPasswordMeta(),
  ]);
  return (
    <AdminDashboard
      initialCatalog={catalog}
      passwordExpiry={{
        warnWithin48h: passwordMeta.warnWithin48h,
        hoursLeft: passwordMeta.hoursLeft,
        expiresAt: passwordMeta.expiresAt,
        updatedAt: passwordMeta.updatedAt,
      }}
    />
  );
}
