import type { Metadata } from "next";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Wado Ryu",
  description:
    "Principes philosophiques, corporels et stratégiques du karaté Wado Ryu.",
};

export default function WadoRyuPage() {
  return (
    <>
      <PageHero
        eyebrow="Discipline"
        title="Le Wado Ryu"
        description="Une forme de karaté fondée par Hironori Otsuka dans les années 1930 : fluidité, vitesse et précision plutôt que force brute."
      />

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <div className="max-w-3xl">
          <h2 className="font-display text-3xl text-paper md:text-4xl">
            Shin · Gi · Tai
          </h2>
          <p className="mt-5 text-paper-muted leading-relaxed">
            Trois concepts fondateurs de la pratique :{" "}
            <strong className="text-paper">Shin</strong> (le cœur, l&apos;esprit,
            l&apos;intention), <strong className="text-paper">Gi</strong> (la
            technique) et <strong className="text-paper">Tai</strong> (le corps).
            Ils s&apos;alimentent mutuellement : la technique fait évoluer le
            corps, puis l&apos;esprit, ouvrant de nouvelles techniques.
          </p>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Seichusen",
              text: "Ligne médiane et alignement postural : dos droit, tête étirée, hanches alignées.",
            },
            {
              title: "Iki ashi",
              text: "Tirer avec le pied pour contrôler le déplacement et éviter le déséquilibre.",
            },
            {
              title: "Uchi Te",
              text: "Pousser avec les mains, presser vers l’avant — sans perte de distance involontaire.",
            },
          ].map((item) => (
            <article
              key={item.title}
              className="border border-line bg-ink-soft p-6"
            >
              <h3 className="font-display text-xl text-gold">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-paper-muted">
                {item.text}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-ink-soft">
        <div className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
            Principes stratégiques
          </p>
          <h2 className="mt-3 font-display text-3xl text-paper md:text-4xl">
            Noru · Nagasu · Inasu
          </h2>
          <div className="mt-12 grid gap-8 lg:grid-cols-3">
            {[
              {
                title: "Noru",
                subtitle: "Rentrer, contrer, pénétrer",
                text: "Cycle Neru / Osae / Nogareru : s’approcher, bloquer ou contrer, puis saisir l’opportunité — fluidité et stratégie.",
              },
              {
                title: "Nagasu",
                subtitle: "Aspirer, accompagner, laisser passer",
                text: "Attirer l’adversaire, utiliser son élan, laisser passer puis enrouler pour contrôler — un flux continu.",
              },
              {
                title: "Inasu",
                subtitle: "Action dans l’esquive",
                text: "Fusion de noru et de la défense : bloquer et contrer en même temps, capitaliser sur l’élan adverse.",
              },
            ].map((item) => (
              <article key={item.title}>
                <h3 className="font-display text-2xl text-paper">{item.title}</h3>
                <p className="mt-1 text-sm text-crimson-bright">{item.subtitle}</p>
                <p className="mt-4 text-sm leading-relaxed text-paper-muted">
                  {item.text}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
          Timing
        </p>
        <h2 className="mt-3 font-display text-3xl text-paper">Les trois sen</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Go no sen",
              text: "Action-réaction : d’abord bloquer, puis contre-attaquer.",
            },
            {
              title: "Sen no sen",
              text: "Action simultanée : blocage et contre initiés avec l’attaque.",
            },
            {
              title: "Sen sen no sen",
              text: "Percevoir l’intention avant l’attaque — inversion apparente des rôles.",
            },
          ].map((item) => (
            <article
              key={item.title}
              className="border-l-2 border-crimson pl-5"
            >
              <h3 className="font-display text-xl text-paper">{item.title}</h3>
              <p className="mt-2 text-sm text-paper-muted">{item.text}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
