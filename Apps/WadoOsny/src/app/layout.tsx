import type { Metadata } from "next";
import { Manrope, Syne } from "next/font/google";
import { SiteShell } from "@/components/SiteShell";
import { getClub } from "@/content/club-data";
import { site } from "@/content/site";
import "./globals.css";

const syne = Syne({
  variable: "--font-syne",
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: `${site.name} — ${site.fullName}`,
    template: `%s | ${site.name}`,
  },
  description:
    "Club de karaté Wado Ryu et TSYR à Osny (Val-d'Oise). Cours enfants, ados et adultes — fluidité, précision, tradition.",
  metadataBase: new URL("https://wado-osny.fr"),
  openGraph: {
    title: site.fullName,
    description: site.tagline,
    locale: "fr_FR",
    type: "website",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const club = await getClub();
  return (
    <html lang="fr" className={`${syne.variable} ${manrope.variable} h-full`}>
      <body className="flex min-h-full flex-col bg-ink text-paper antialiased">
        <SiteShell club={club}>{children}</SiteShell>
      </body>
    </html>
  );
}
