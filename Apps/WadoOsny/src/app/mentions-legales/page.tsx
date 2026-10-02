import type { Metadata } from "next";
import { PageHero } from "@/components/PageHero";
import { getClub } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Mentions légales",
};

export default async function MentionsLegalesPage() {
  const club = await getClub();
  return (
    <>
      <PageHero eyebrow="Légal" title="Mentions légales" />
      <section className="mx-auto max-w-3xl space-y-10 px-5 py-16 text-paper-muted leading-relaxed md:px-8">
        <p className="text-sm">En vigueur au 15/07/2024</p>
        <div>
          <h2 className="font-display text-2xl text-paper">Article 1 — L&apos;éditeur</h2>
          <p className="mt-4">
            L&apos;édition du site est assurée par l&apos;{club.association},
            association déclarée (loi 1901), immatriculée au Répertoire National
            des Associations sous le numéro RNA {club.rna}, dont le siège social
            est situé au {club.siege}.
          </p>
          <p className="mt-3">
            Adresse e-mail :{" "}
            <a href={`mailto:${club.email}`} className="text-gold">
              {club.email}
            </a>
          </p>
          <p className="mt-3">
            Le Directeur de la publication est Anthony Gilson.
          </p>
        </div>
        <div>
          <h2 className="font-display text-2xl text-paper">Article 2 — L&apos;hébergeur</h2>
          <p className="mt-4">
            Le site est hébergé sur un serveur OVH (2 rue Kellermann, 59100
            Roubaix).
          </p>
        </div>
        <div>
          <h2 className="font-display text-2xl text-paper">Article 3 — Accès</h2>
          <p className="mt-4">
            Le site est accessible 7j/7, 24h/24 sauf cas de force majeure ou
            maintenance. L&apos;éditeur ne saurait être tenu responsable en cas
            d&apos;interruption.
          </p>
        </div>
        <div>
          <h2 className="font-display text-2xl text-paper">Article 4 — Données</h2>
          <p className="mt-4">
            Conformément à la loi Informatique et Libertés, vous disposez d&apos;un
            droit d&apos;accès, de rectification, de suppression et d&apos;opposition
            sur vos données personnelles, exercé par mail à {club.email}.
          </p>
        </div>
      </section>
    </>
  );
}
