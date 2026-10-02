import type { Metadata } from "next";
import "./admin.css";

export const metadata: Metadata = {
  title: "Admin club",
  robots: { index: false, follow: false },
};

export default function DojoAdminRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="admin-root">{children}</div>;
}
