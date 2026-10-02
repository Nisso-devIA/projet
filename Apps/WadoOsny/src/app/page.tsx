import Image from "next/image";
import Link from "next/link";
import { getClub, getInstructors } from "@/content/club-data";

export default async function HomePage() {
  const [club, instructors] = await Promise.all([getClub(), getInstructors()]);

  return (
    <>
      <section className="relative min-h-[100svh] overflow-hidden">
        <Image
          src="/images/hero.jpg"
          alt="Cours de karaté Wado Ryu à Osny"
          fill
          priority
          className="object-cover object-[center_30%]"
          sizes="100vw"
        />
        <div
          className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/35"
          aria-hidden
        />
        <div
          className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-ink/50"
          aria-hidden
        />
        <div className="grain absolute inset-0" aria-hidden />

        <div className="relative z-[2] mx-auto flex min-h-[100svh] max-w-7xl flex-col justify-end px-5 pb-16 pt-32 md:justify-center md:px-8 md:pb-24">
          <p className="animate-rise text-xs font-semibold uppercase tracking-[0.32em] text-gold">
            {club.tagline}
          </p>
          <h1 className="animate-rise-delay-1 mt-5 max-w-3xl font-display text-5xl leading-[0.95] tracking-tight text-paper md:text-7xl lg:text-8xl">
            {club.name}
          </h1>
          <p className="animate-rise-delay-2 mt-6 max-w-xl text-lg text-paper/85 md:text-xl">
            Karaté Wado Ryu &amp; TSYR — fluidité, vitesse et précision au cœur
            du Val-d&apos;Oise.
          </p>
          <div className="animate-rise-delay-3 mt-10 flex flex-wrap gap-4">
            <Link
              href="/horaires"
              className="rounded-sm bg-crimson px-6 py-3.5 text-sm font-semibold text-paper transition hover:bg-crimson-bright"
            >
              Voir les horaires
            </Link>
            <Link
              href="/contact"
              className="rounded-sm border border-paper/30 px-6 py-3.5 text-sm font-semibold text-paper transition hover:border-paper hover:bg-paper/5"
            >
              Essayer un cours
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 md:px-8 md:py-28">
        <div className="grid items-end gap-8 md:grid-cols-[1fr_1.2fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
              Nos disciplines
            </p>
            <h2 className="mt-4 font-display text-3xl text-paper md:text-5xl">
              Deux voies, une exigence
            </h2>
          </div>
          <p className="max-w-xl text-paper-muted md:justify-self-end">
            Du karaté japonais fluide aux principes du jujutsu classique : une
            pratique complète pour enfants, ados et adultes.
          </p>
        </div>

        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <Link
            href="/wado-ryu"
            className="group relative overflow-hidden border border-line bg-ink-soft"
          >
            <div className="relative aspect-[16/10]">
              <Image
                src="/images/cours-2.jpg"
                alt="Pratique du Wado Ryu"
                fill
                className="object-cover transition duration-700 group-hover:scale-105"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/40 to-transparent" />
            </div>
            <div className="relative p-7 md:p-9">
              <h3 className="font-display text-3xl text-paper">Le Wado Ryu</h3>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-paper-muted">
                Fondé par Hironori Otsuka dans les années 1930 : mélange de
                karaté traditionnel et de ju-jutsu. Fluidité, vitesse et
                précision plutôt que force brute.
              </p>
              <span className="mt-6 inline-flex text-sm font-medium text-gold transition group-hover:text-crimson-bright">
                Découvrir →
              </span>
            </div>
          </Link>

          <Link
            href="/tsyr"
            className="group relative overflow-hidden border border-line bg-ink-soft"
          >
            <div className="relative aspect-[16/10]">
              <Image
                src="/images/tobin-threadgill.jpg"
                alt="Pratique du TSYR"
                fill
                className="object-cover transition duration-700 group-hover:scale-105"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/40 to-transparent" />
            </div>
            <div className="relative p-7 md:p-9">
              <h3 className="font-display text-3xl text-paper">Le TSYR</h3>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-paper-muted">
                Takamura ha Shindo Yoshin Ryu — jujutsu et kenjutsu. Posture,
                précision du mouvement, unité entre attaque et défense.
              </p>
              <span className="mt-6 inline-flex text-sm font-medium text-gold transition group-hover:text-crimson-bright">
                Découvrir →
              </span>
            </div>
          </Link>
        </div>
      </section>

      <section className="border-y border-line bg-ink-soft">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 md:grid-cols-2 md:items-center md:px-8 md:py-28">
          <div className="relative aspect-[4/5] overflow-hidden md:aspect-[5/6]">
            <Image
              src="/images/groupe-1.jpg"
              alt="Groupe de pratiquants Wado-Osny"
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 50vw"
            />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
              Le club
            </p>
            <h2 className="mt-4 font-display text-3xl text-paper md:text-5xl">
              Un dojo vivant à Osny
            </h2>
            <p className="mt-6 text-base leading-relaxed text-paper-muted">
              Cours enfants dès 5 ans, ados et adultes : Wado Ryu, self-défense,
              karaté contact et TSYR. Une équipe d&apos;instructeurs diplômés
              FFK vous accompagne tout au long de la saison.
            </p>
            <ul className="mt-8 space-y-3 text-sm text-paper/90">
              <li className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-crimson-bright" />
                Programme progressif par âge (petits, moyens, grands)
              </li>
              <li className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-crimson-bright" />
                Deux lieux de pratique à Osny
              </li>
              <li className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-crimson-bright" />
                Tradition japonaise et approche contemporaine
              </li>
            </ul>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link
                href="/instructeurs"
                className="rounded-sm bg-crimson px-5 py-3 text-sm font-medium text-paper transition hover:bg-crimson-bright"
              >
                Rencontrer l&apos;équipe
              </Link>
              <Link
                href="/tarifs"
                className="rounded-sm border border-line px-5 py-3 text-sm font-medium text-paper transition hover:border-paper/40"
              >
                Consulter les tarifs
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 md:px-8 md:py-28">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
              Les instructeurs
            </p>
            <h2 className="mt-4 font-display text-3xl text-paper md:text-5xl">
              Maîtres &amp; passion
            </h2>
          </div>
          <Link
            href="/instructeurs"
            className="text-sm font-medium text-gold hover:text-crimson-bright"
          >
            Voir toute l&apos;équipe →
          </Link>
        </div>
        <div className="mt-12 grid gap-8 sm:grid-cols-3">
          {instructors.map((person) => (
            <article key={person.id} className="group">
              <div className="relative aspect-[3/4] overflow-hidden bg-ink-lift">
                <Image
                  src={person.image}
                  alt={person.name}
                  fill
                  className="object-cover grayscale transition duration-700 group-hover:scale-105 group-hover:grayscale-0"
                  sizes="(max-width: 640px) 100vw, 33vw"
                />
              </div>
              <h3 className="mt-5 font-display text-2xl text-paper">
                {person.name}
              </h3>
              <p className="mt-2 text-sm text-paper-muted">{person.ranks[0]}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative overflow-hidden border-t border-line">
        <Image
          src="/images/groupe-enfants.jpg"
          alt=""
          fill
          className="object-cover opacity-30"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-ink/80" aria-hidden />
        <div className="relative z-[2] mx-auto max-w-3xl px-5 py-24 text-center md:px-8">
          <h2 className="font-display text-3xl text-paper md:text-5xl">
            Prêt à monter sur le tatami&nbsp;?
          </h2>
          <p className="mt-5 text-paper-muted">
            Premiers cours d&apos;essai sur demande. Écrivez-nous, nous vous
            indiquerons le créneau adapté.
          </p>
          <Link
            href="/contact"
            className="mt-8 inline-flex rounded-sm bg-crimson px-6 py-3.5 text-sm font-semibold text-paper transition hover:bg-crimson-bright"
          >
            Nous contacter
          </Link>
        </div>
      </section>
    </>
  );
}
