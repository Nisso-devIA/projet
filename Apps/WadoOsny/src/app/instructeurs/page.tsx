import type { Metadata } from "next";
import Image from "next/image";
import { PageHero } from "@/components/PageHero";
import { getInstructors } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Instructeurs",
  description:
    "Équipe pédagogique de Wado-Osny — instructeurs Wado Ryu et TSYR.",
};

export default async function InstructeursPage() {
  const instructors = await getInstructors();

  return (
    <>
      <PageHero
        eyebrow="Équipe"
        title="Les instructeurs"
        description="Des maîtres et instructeurs passionnés qui guident nos élèves avec expertise et dévouement."
      />

      <section className="mx-auto max-w-7xl space-y-20 px-5 py-16 md:px-8 md:py-24">
        {instructors.map((person, i) => (
          <article
            key={person.id}
            className={`grid gap-10 lg:grid-cols-2 lg:items-center ${
              i % 2 === 1 ? "lg:[&>*:first-child]:order-2" : ""
            }`}
          >
            <div className="relative aspect-[4/5] overflow-hidden bg-ink-lift">
              {person.image ? (
                <Image
                  src={person.image}
                  alt={person.name}
                  fill
                  className="object-cover"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
              ) : null}
            </div>
            <div>
              <h2 className="font-display text-3xl text-paper md:text-4xl">
                {person.name}
              </h2>
              <ul className="mt-4 space-y-1">
                {person.ranks.map((rank) => (
                  <li
                    key={rank}
                    className="text-sm font-medium text-crimson-bright"
                  >
                    {rank}
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-base leading-relaxed text-paper-muted">
                {person.bio}
              </p>
            </div>
          </article>
        ))}
      </section>
    </>
  );
}
