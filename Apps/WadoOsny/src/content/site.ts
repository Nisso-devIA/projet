export type NavItem =
  | { href: string; label: string }
  | { label: string; children: { href: string; label: string }[] };

/** Branding de secours (Header client) — le détail club vient de data/club.json. */
export const site = {
  name: "Wado-Osny",
  fullName: "Karaté Wado Ryu Osny",
  tagline: "Club de karaté en Île-de-France",
} as const;

export const nav: NavItem[] = [
  { href: "/", label: "Accueil" },
  {
    label: "Nos disciplines",
    children: [
      { href: "/wado-ryu", label: "Wado Ryu" },
      { href: "/tsyr", label: "Le TSYR" },
      { href: "/historique", label: "Historique" },
    ],
  },
  { href: "/instructeurs", label: "Les instructeurs" },
  {
    label: "Infos pratiques",
    children: [
      { href: "/tarifs", label: "Tarifs" },
      { href: "/horaires", label: "Horaires" },
      { href: "/calendrier", label: "Calendrier" },
    ],
  },
  { href: "/mediatheque", label: "Médiathèque" },
  { href: "/contact", label: "Contact" },
];

export function navItemIsActive(item: NavItem, pathname: string): boolean {
  if ("href" in item) {
    return item.href === "/"
      ? pathname === "/"
      : pathname.startsWith(item.href);
  }
  return item.children.some(
    (child) =>
      pathname === child.href || pathname.startsWith(`${child.href}/`),
  );
}
