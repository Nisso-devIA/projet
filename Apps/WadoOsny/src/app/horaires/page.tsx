import type { Metadata } from "next";
import { Locations } from "@/components/Locations";
import { PageHero } from "@/components/PageHero";
import { getClub, getSchedules } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Horaires",
  description:
    "Horaires des cours enfants, ados et adultes — Wado Ryu, self-défense, karaté contact et TSYR à Osny.",
};

export default async function HorairesPage() {
  const [schedules, club] = await Promise.all([getSchedules(), getClub()]);

  return (
    <>
      <PageHero
        eyebrow="Planning"
        title="Horaires"
        description="Un programme progressif pour les enfants, et des cours complémentaires pour ados et adultes."
        cta={{ href: "/contact", label: "Réserver un essai" }}
      />

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
        <h2 className="font-display text-3xl text-paper">Cours enfants</h2>
        <p className="mt-4 max-w-3xl text-paper-muted leading-relaxed">
          Pour les petits (5–6 ans), l&apos;accent est mis sur la motricité.
          Les moyens (7–9 ans) approfondissent la pratique traditionnelle et
          s&apos;initient à la compétition. Les grands (9–12 ans) travaillent
          les spécificités du Wado Ryu et la préparation aux compétitions.
        </p>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {schedules.kids.map((group) => (
            <article
              key={group.id}
              className="border border-line bg-ink-soft p-6"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">
                {group.ages}
              </p>
              <h3 className="mt-2 font-display text-2xl text-paper">
                {group.group}
              </h3>
              <p className="mt-3 text-sm text-paper-muted">{group.focus}</p>
              <ul className="mt-6 space-y-3 border-t border-line pt-5">
                {group.slots.map((slot) => (
                  <li
                    key={`${slot.day}-${slot.time}`}
                    className="flex flex-col gap-0.5 text-sm"
                  >
                    <span className="font-medium text-paper">
                      {slot.day} · {slot.time}
                    </span>
                    <span className="text-paper-muted">{slot.place}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-ink-soft">
        <div className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
          <h2 className="font-display text-3xl text-paper">
            Cours ados / adultes
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-2">
            {schedules.adults.map((course) => (
              <article
                key={course.id}
                className="border border-line bg-ink p-6"
              >
                <h3 className="font-display text-2xl text-paper">
                  {course.title}
                </h3>
                <p className="mt-2 text-sm text-paper-muted">
                  {course.description}
                </p>
                <ul className="mt-5 space-y-2">
                  {course.slots.map((slot) => (
                    <li
                      key={`${course.id}-${slot.day}`}
                      className="text-sm text-paper/90"
                    >
                      <span className="text-gold">{slot.day}</span>{" "}
                      {slot.time} — {slot.place}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
        <Locations club={club} showTitle />
      </section>
    </>
  );
}
