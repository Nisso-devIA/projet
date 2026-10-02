"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutAdmin } from "@/app/dojo-admin/actions";
import { adminPath } from "@/lib/admin-paths";

const links = [
  { href: "", label: "Accueil" },
  { href: "/evenements", label: "Événements" },
  { href: "/mediatheque", label: "Photos" },
  { href: "/horaires", label: "Horaires" },
  { href: "/tarifs", label: "Tarifs" },
  { href: "/instructeurs", label: "Instructeurs" },
  { href: "/club", label: "Club" },
  { href: "/mot-de-passe", label: "Mot de passe" },
];

export function AdminNav({ passwordExpired }: { passwordExpired: boolean }) {
  const pathname = usePathname();
  return (
    <nav className="admin-nav" aria-label="Admin">
      {links.map((link) => {
        const href = adminPath(link.href);
        const current =
          link.href === ""
            ? pathname === adminPath()
            : pathname.startsWith(href);
        return (
          <Link
            key={link.href || "home"}
            href={href}
            aria-current={current ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
      <form action={logoutAdmin}>
        <button type="submit" className="admin-btn-ghost admin-btn">
          Déconnexion
        </button>
      </form>
      {passwordExpired ? (
        <span className="admin-error">Mot de passe à renouveler</span>
      ) : null}
    </nav>
  );
}
