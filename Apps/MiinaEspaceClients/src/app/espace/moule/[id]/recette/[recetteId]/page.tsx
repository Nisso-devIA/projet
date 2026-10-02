import Link from "next/link";
import { notFound } from "next/navigation";
import { EspaceSocialLinks } from "@/components/espace/EspaceSocialLinks";
import { FlipPdfReader } from "@/components/FlipPdfReader";
import { getRecette, recetteFlipReady } from "@/lib/store";

type Props = { params: Promise<{ id: string; recetteId: string }> };

export const dynamic = "force-dynamic";

export default async function RecetteReaderPage({ params }: Props) {
  const { id, recetteId } = await params;
  const found = await getRecette(id, recetteId);
  if (!found) notFound();

  const { moule, recette } = found;

  if (!recetteFlipReady(recette)) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[#2a211c] px-4 text-center text-white">
        <p className="font-display text-2xl">Feuilletage en préparation</p>
        <p className="max-w-md text-sm text-white/70">
          Les pages de cette recette ne sont pas encore prêtes. Réessayez après
          un nouvel upload dans l’admin.
        </p>
        <Link
          href={`/espace/moule/${moule.id}`}
          className="rounded-full bg-white/15 px-4 py-2 text-sm font-bold hover:bg-white/25"
        >
          Retour au sommaire
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[#2a211c]">
      <header className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3 text-white sm:px-6">
        <div className="min-w-0">
          <p className="text-[0.65rem] font-semibold tracking-[0.12em] text-white/60 uppercase">
            {moule.title}
          </p>
          <h1 className="truncate font-display text-xl font-semibold">
            {recette.title}
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <EspaceSocialLinks variant="dark" />
          <Link
            href={`/espace/moule/${moule.id}`}
            className="rounded-full bg-white/15 px-4 py-2 text-sm font-bold hover:bg-white/25"
          >
            Sommaire
          </Link>
        </div>
      </header>
      <FlipPdfReader
        mouleId={moule.id}
        recetteId={recette.id}
        pageCount={recette.flipPageCount!}
        title={recette.title}
      />
    </div>
  );
}
