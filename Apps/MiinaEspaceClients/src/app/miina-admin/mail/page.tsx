import { AdminShell } from "@/components/admin/AdminShell";
import { InviteClientForm } from "@/components/admin/InviteClientForm";
import { getAdminPasswordMeta } from "@/lib/admin-auth";

export const dynamic = "force-dynamic";

export default async function AdminMailPage() {
  const passwordMeta = await getAdminPasswordMeta();
  return (
    <AdminShell
      title="Mail clientes"
      active="mail"
      passwordExpiry={{
        warnWithin48h: passwordMeta.warnWithin48h,
        hoursLeft: passwordMeta.hoursLeft,
        expiresAt: passwordMeta.expiresAt,
        updatedAt: passwordMeta.updatedAt,
      }}
    >
      <InviteClientForm />
    </AdminShell>
  );
}
