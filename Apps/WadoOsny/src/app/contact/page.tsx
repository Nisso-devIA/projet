import type { Metadata } from "next";
import { ContactForm } from "@/components/ContactForm";
import { Locations } from "@/components/Locations";
import { PageHero } from "@/components/PageHero";
import { getClub } from "@/content/club-data";
import { site } from "@/content/site";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contactez ${site.name}`,
};

export default async function ContactPage() {
  const club = await getClub();
  return (
    <>
      <PageHero
        eyebrow="Écrire au club"
        title="Nous contacter"
        description="Tous les champs marqués d’un astérisque (*) sont à renseigner."
      />

      <section className="mx-auto max-w-3xl px-5 py-16 md:px-8 md:py-20">
        <h2 className="font-display text-2xl text-paper">Message</h2>
        <div className="mt-8">
          <ContactForm email={club.email} />
        </div>
        <p className="mt-8 text-sm text-paper-muted">
          Ou directement :{" "}
          <a
            href={`mailto:${club.email}`}
            className="text-gold hover:underline"
          >
            {club.email}
          </a>
        </p>
      </section>

      <section className="border-t border-line">
        <div className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
          <Locations club={club} showTitle />
        </div>
      </section>
    </>
  );
}
