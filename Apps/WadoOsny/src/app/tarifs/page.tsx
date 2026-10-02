import type { Metadata } from "next";
import Link from "next/link";
import { Locations } from "@/components/Locations";
import { PageHero } from "@/components/PageHero";
import { getClub, getPricing } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Tarifs",
  description:
    "Cotisations club et licence fédérale — cours enfants, ados/adultes, self-défense et karaté contact.",
};

export default async function TarifsPage() {
  const [pricing, club] = await Promise.all([getPricing(), getClub()]);

  return (
    <>
      <PageHero
        eyebrow="Saison"
        title="Tarifs"
        description="Cotisations annuelles du club. La licence fédérale FFK s’ajoute selon les formules."
      />

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <div className="grid gap-6 lg:grid-cols-3">
          {pricing.map((plan) => (
            <article
              key={plan.id}
              className="flex flex-col border border-line bg-ink-soft p-8"
            >
              <h2 className="font-display text-2xl text-paper">{plan.title}</h2>
              <p className="mt-8 text-xs uppercase tracking-[0.2em] text-paper-muted">
                Cotisation club
              </p>
              <p className="mt-2 font-display text-5xl text-paper">
                {plan.club}
                <span className="text-2xl text-gold">€</span>
              </p>
              {plan.license != null ? (
                <p className="mt-4 text-sm text-paper-muted">
                  + licence fédérale{" "}
                  <span className="font-semibold text-paper">
                    {plan.license}€
                  </span>
                </p>
              ) : (
                <p className="mt-4 text-sm text-paper-muted">&nbsp;</p>
              )}
              <p className="mt-6 flex-1 text-sm text-paper-muted">{plan.note}</p>
              <Link
                href="/contact"
                className="mt-8 inline-flex justify-center rounded-sm bg-crimson px-4 py-3 text-sm font-medium text-paper transition hover:bg-crimson-bright"
              >
                S&apos;inscrire
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t border-line">
        <div className="mx-auto max-w-7xl px-5 py-16 md:px-8">
          <Locations club={club} showTitle />
        </div>
      </section>
    </>
  );
}
