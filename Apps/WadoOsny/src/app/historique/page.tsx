import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Historique",
  description:
    "Hironori Otsuka et l’histoire du Wado Ryu — des origines du Shindo Yoshin Ryu à 1934.",
};

export default function HistoriquePage() {
  return (
    <>
      <PageHero
        eyebrow="Tradition"
        title="Historique"
        description="Otsuka Hironori & histoire du Wado Ryu."
      />

      <section className="mx-auto max-w-3xl px-5 py-16 md:px-8 md:py-24">
        <div className="space-y-6 text-paper-muted leading-relaxed">
          <p>
            Le Wado Ryu est un style de karaté fondé dans les années 1930 par
            Hironori Otsuka. Basé sur la pratique du jujutsu et des principes
            du kenjutsu, il est souvent qualifié de premier style de karaté
            « purement » japonais.
          </p>
          <p>
            Hironori Otsuka est né le 1<sup>er</sup> juin 1892 à Shimodate
            (préfecture d&apos;Ibaraki). En 1897, il commence l&apos;apprentissage
            du Shindo Yoshin Ryu avec Shinzaburo Nakayama, alors 3<sup>e</sup>{" "}
            directeur de l&apos;école. En 1920, à 28 ans, il reçoit le plus haut
            degré d&apos;enseignement du style.
          </p>
          <p>
            En 1922, il rencontre Gichin Funakoshi, fondateur du karaté
            Shotokan, et étudie ses principes et techniques. En 1934, le style
            Wado Ryu est officiellement reconnu sous le nom{" "}
            <em>Wado Ryu Jujutsu Kempo</em> — synthèse de percussions
            pieds/poings, éléments de jujutsu (étranglements, clefs de bras…) et
            principes issus du kenjutsu.
          </p>
        </div>
        <Link
          href="/wado-ryu"
          className="mt-12 inline-flex text-sm font-medium text-gold hover:text-crimson-bright"
        >
          Lire les principes du Wado Ryu →
        </Link>
      </section>
    </>
  );
}
