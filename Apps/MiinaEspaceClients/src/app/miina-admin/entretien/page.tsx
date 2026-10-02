import { AdminEntretien } from "@/components/admin/AdminEntretien";
import { getAdminPasswordMeta } from "@/lib/admin-auth";
import { readCatalog } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function AdminEntretienPage() {
  const [catalog, passwordMeta] = await Promise.all([
    readCatalog(),
    getAdminPasswordMeta(),
  ]);
  return (
    <AdminEntretien
      initialHref={catalog.entretienHref}
      initialFlipPageCount={catalog.entretienFlipPageCount ?? 0}
      initialOriginalName={catalog.entretienOriginalName}
      passwordExpiry={{
        warnWithin48h: passwordMeta.warnWithin48h,
        hoursLeft: passwordMeta.hoursLeft,
        expiresAt: passwordMeta.expiresAt,
        updatedAt: passwordMeta.updatedAt,
      }}
    />
  );
}
