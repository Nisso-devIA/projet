import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/PageHero";
import {
  formatEventDate,
  getEvents,
  splitEvents,
} from "@/content/club-data";

export const metadata: Metadata = {
  title: "Calendrier",
  description:
    "Prochains événements du club Wado-Osny — stages, cours et rencontres.",
};

export default async function CalendrierPage() {
  const events = await getEvents();
  const { upcoming, past } = splitEvents(events);

  return (
    <>
      <PageHero
        eyebrow="Agenda"
        title="Calendrier"
        description="Stages, cours exceptionnels et événements du club."
        cta={{ href: "/horaires", label: "Voir les horaires hebdo" }}
      />

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
        <h2 className="font-display text-2xl text-paper md:text-3xl">
          Prochains événements
        </h2>
        {upcoming.length === 0 ? (
          <div className="mt-8 border border-line bg-ink-soft px-6 py-10 text-center">
            <p className="text-paper-muted">
              Il n’y a pas d’événements à venir pour le moment.
            </p>
            <Link
              href="/contact"
              className="mt-5 inline-flex text-sm font-medium text-gold hover:text-crimson-bright"
            >
              Nous écrire pour être informé →
            </Link>
          </div>
        ) : (
          <ul className="mt-10 space-y-6">
            {upcoming.map((event) => (
              <li
                key={event.id}
                className="grid gap-4 border border-line bg-ink-soft p-6 md:grid-cols-[10rem_1fr]"
              >
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold">
                    {formatEventDate(event.date)}
                  </p>
                  <p className="mt-2 text-sm text-paper-muted">{event.time}</p>
                </div>
                <div>
                  <h3 className="font-display text-xl text-paper">
                    {event.title}
                  </h3>
                  <p className="mt-2 text-sm text-paper-muted">{event.place}</p>
                  <p className="mt-3 text-sm leading-relaxed text-paper/85">
                    {event.description}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border-t border-line bg-ink-soft">
        <div className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-20">
          <h2 className="font-display text-2xl text-paper md:text-3xl">
            Derniers événements passés
          </h2>
          <ul className="mt-10 space-y-6">
            {past.map((event) => (
              <li
                key={event.id}
                className="grid gap-4 border border-line bg-ink p-6 md:grid-cols-[10rem_1fr]"
              >
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold">
                    {formatEventDate(event.date)}
                  </p>
                  <p className="mt-2 text-sm text-paper-muted">{event.time}</p>
                </div>
                <div>
                  <h3 className="font-display text-xl text-paper">
                    {event.title}
                  </h3>
                  <p className="mt-2 text-sm text-paper-muted">{event.place}</p>
                  <p className="mt-3 text-sm leading-relaxed text-paper/85">
                    {event.description}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}
