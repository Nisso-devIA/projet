import type { Metadata } from "next";
import Image from "next/image";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "TSYR",
  description:
    "Takamura ha Shindo Yoshin Ryu — jujutsu, kenjutsu et arts martiaux traditionnels à Osny.",
};

export default function TsyrPage() {
  return (
    <>
      <PageHero
        eyebrow="Discipline"
        title="Le TSYR"
        description="Takamura ha Shindo Yoshin Ryu : école de jujutsu et kenjutsu transmise de maître à élève depuis 1864."
      />

      <section className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="font-display text-3xl text-paper md:text-4xl">
              Un sogo bujutsu
            </h2>
            <p className="mt-5 text-paper-muted leading-relaxed">
              L&apos;école intègre techniques à mains nues, sabre, dégainage,
              couteau et autres armes typiques des samouraïs. La pratique à
              mains nues couvre dégagements, déséquilibre, projections, clés,
              atémis, étranglements et désarmements — le tout en kata à deux
              partenaires, avec un travail solo pour la posture et la force
              interne.
            </p>
            <p className="mt-4 text-paper-muted leading-relaxed">
              Le curriculum compte trois niveaux (shoden, chuden, joden) et
              environ 305 kata au total. La transmission inclut aussi le{" "}
              <em>reigi</em> — étiquette, savoir et traditions.
            </p>
          </div>
          <div className="relative aspect-[4/3] overflow-hidden">
            <Image
              src="/images/tobin-threadgill.jpg"
              alt="Toby Threadgill, représentant du TSYR"
              fill
              className="object-cover"
              sizes="(max-width: 1024px) 100vw, 50vw"
            />
          </div>
        </div>
      </section>

      <section className="border-y border-line bg-ink-soft">
        <div className="mx-auto max-w-3xl px-5 py-16 md:px-8 md:py-24">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold">
            Histoire
          </p>
          <h2 className="mt-3 font-display text-3xl text-paper">
            De 1864 jusqu&apos;à Osny
          </h2>
          <p className="mt-6 text-paper-muted leading-relaxed">
            Fondée au Japon à la fin de l&apos;ère féodale, l&apos;école
            Shindo Yoshin Ryu dans la lignée Ohbata / Takamura est aujourd&apos;hui
            dirigée par sensei Toby Threadgill (hombu dojo au Colorado). Elle
            met l&apos;accent sur le déséquilibre avec une posture verticale
            économique — une puissance qui ne repose pas sur la force brute.
          </p>
          <p className="mt-4 text-sm text-paper-muted/80">
            Crédit article source : Nicolas Delalondre
          </p>
        </div>
      </section>
    </>
  );
}
