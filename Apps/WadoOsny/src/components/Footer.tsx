import Link from "next/link";
import { nav } from "@/content/site";
import type { ClubInfo } from "@/content/defaults";

export function Footer({ club }: { club: ClubInfo }) {
  return (
    <footer className="mt-auto border-t border-line bg-ink-soft">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-[1.2fr_1fr_1fr] md:px-8">
        <div>
          <p className="font-display text-2xl text-paper">{club.name}</p>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-paper-muted">
            {club.fullName} — {club.tagline}. Pratique du Wado Ryu et du TSYR
            à Osny (Val-d&apos;Oise).
          </p>
          <a
            href={`mailto:${club.email}`}
            className="mt-5 inline-block text-sm text-gold transition hover:text-paper"
          >
            {club.email}
          </a>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-paper-muted">
            Navigation
          </p>
          <ul className="mt-4 space-y-2">
            {nav.flatMap((item) =>
              "href" in item
                ? [
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className="text-sm text-paper/85 transition hover:text-crimson-bright"
                      >
                        {item.label}
                      </Link>
                    </li>,
                  ]
                : item.children.map((child) => (
                    <li key={child.href}>
                      <Link
                        href={child.href}
                        className="text-sm text-paper/85 transition hover:text-crimson-bright"
                      >
                        {child.label}
                      </Link>
                    </li>
                  )),
            )}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-paper-muted">
            Lieux
          </p>
          <ul className="mt-4 space-y-4">
            {club.locations.map((loc) => (
              <li key={loc.name} className="text-sm text-paper/85">
                <span className="block font-medium text-paper">{loc.short}</span>
                {loc.address}
                <br />
                {loc.city}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-5 text-xs text-paper-muted md:flex-row md:items-center md:justify-between md:px-8">
          <p>
            © {new Date().getFullYear()} {club.association}
          </p>
          <div className="flex gap-5">
            <Link href="/mentions-legales" className="hover:text-paper">
              Mentions légales
            </Link>
            <Link href="/confidentialite" className="hover:text-paper">
              Confidentialité
            </Link>
            <Link href="/historique" className="hover:text-paper">
              Historique
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
