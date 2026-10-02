import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { EspaceSocialLinks } from "@/components/espace/EspaceSocialLinks";
import {
  getMoule,
  mouleHasRecettes,
  recetteFlipReady,
  recetteKindLabel,
  type RecetteFile,
  type RecetteKind,
} from "@/lib/store";

type Props = { params: Promise<{ id: string }> };

export const dynamic = "force-dynamic";

const KIND_ORDER: RecetteKind[] = ["sucre", "sale"];

function RecetteRow({
  mouleId,
  recette,
}: {
  mouleId: string;
  recette: RecetteFile;
}) {
  const ready = recetteFlipReady(recette);
  const href = `/espace/moule/${mouleId}/recette/${recette.id}`;
  if (ready) {
    return (
      <Link
        href={href}
        className="flex items-center gap-3 rounded-2xl bg-card px-4 py-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <span className="min-w-0 flex-1 font-display text-[1.2rem] font-semibold text-ink sm:text-[1.35rem]">
          {recette.title}
        </span>
        <span className="shrink-0 text-xs font-bold tracking-wide text-accent uppercase">
          Ouvrir
        </span>
      </Link>
    );
  }
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-card/60 px-4 py-4 opacity-70">
      <span className="min-w-0 flex-1 font-display text-[1.2rem] font-semibold text-ink sm:text-[1.35rem]">
        {recette.title}
      </span>
      <span className="shrink-0 text-xs text-ink-soft">Bientôt</span>
    </div>
  );
}

export default async function MouleSommairePage({ params }: Props) {
  const { id } = await params;
  const moule = await getMoule(id);
  if (!moule) notFound();

  if (!mouleHasRecettes(moule)) {
    if (moule.fallbackHref) redirect(moule.fallbackHref);
    notFound();
  }

  const byKind = KIND_ORDER.map((kind) => ({
    kind,
    label: recetteKindLabel(kind),
    items: moule.recettes.filter((r) => (r.kind ?? "sucre") === kind),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="relative min-h-dvh">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[#faf2e6]/78"
      />
      <div className="relative">
      <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-ink/10 bg-[#faf2e6]/55 px-4 py-3 backdrop-blur-sm sm:px-6">
        <div className="min-w-0">
          <p className="text-[0.65rem] font-semibold tracking-[0.12em] text-ink-soft uppercase">
            Sommaire
          </p>
          <h1 className="truncate font-display text-xl font-semibold text-ink">
            {moule.title}
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <EspaceSocialLinks />
          <Link
            href="/espace"
            className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-white hover:bg-accent-strong"
          >
            Retour
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-lg px-4 py-8 sm:px-6">
        <p className="font-display mb-6 text-center text-[1.45rem] leading-relaxed font-semibold text-ink sm:text-[1.65rem]">
          Choisissez une recette
        </p>
        <div className="flex flex-col gap-8">
          {byKind.map((group) => (
            <section key={group.kind} aria-labelledby={`cat-${group.kind}`}>
              <h2
                id={`cat-${group.kind}`}
                className="font-display mb-3 text-center text-[1.35rem] font-bold tracking-wide text-accent uppercase sm:text-[1.5rem]"
              >
                {group.label}
              </h2>
              <ul className="flex list-none flex-col gap-3 p-0">
                {group.items.map((recette) => (
                  <li key={recette.id}>
                    <RecetteRow mouleId={moule.id} recette={recette} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </main>
      </div>
    </div>
  );
}
