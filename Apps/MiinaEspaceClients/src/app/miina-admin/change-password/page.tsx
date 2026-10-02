import { cookies } from "next/headers";
import { AdminChangePasswordForm } from "@/components/admin/AdminChangePasswordForm";
import {
  ADMIN_MUST_CHANGE_COOKIE,
  ADMIN_PASSWORD_MAX_AGE_DAYS,
} from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function AdminChangePasswordPage() {
  const jar = await cookies();
  const forced = jar.get(ADMIN_MUST_CHANGE_COOKIE)?.value === "1";

  return (
    <div className="flex min-h-dvh items-center justify-center px-4 py-12">
      <AdminChangePasswordForm
        forced={forced}
        maxAgeDays={ADMIN_PASSWORD_MAX_AGE_DAYS}
      />
    </div>
  );
}
