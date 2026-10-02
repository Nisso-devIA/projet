import { redirect } from "next/navigation";
import { isAdminLoggedIn } from "@/lib/admin-auth";
import { adminPath } from "@/lib/admin-paths";
import { isPasswordExpired } from "@/lib/admin-store";
import { AdminNav } from "@/components/admin/AdminNav";

export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (!(await isAdminLoggedIn())) redirect(adminPath("/login"));
  const expired = await isPasswordExpired();
  return (
    <div className="admin-wrap">
      <AdminNav passwordExpired={expired} />
      {children}
    </div>
  );
}
