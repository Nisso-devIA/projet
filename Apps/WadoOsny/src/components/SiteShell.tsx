"use client";

import { usePathname } from "next/navigation";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import type { ClubInfo } from "@/content/defaults";

export function SiteShell({
  children,
  club,
}: {
  children: React.ReactNode;
  club: ClubInfo;
}) {
  const pathname = usePathname();
  if (pathname.startsWith("/dojo-admin")) {
    return <>{children}</>;
  }
  return (
    <>
      <Header brandName={club.name} />
      <main className="flex-1">{children}</main>
      <Footer club={club} />
    </>
  );
}
