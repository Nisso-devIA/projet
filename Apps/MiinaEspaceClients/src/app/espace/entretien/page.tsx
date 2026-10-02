import Link from "next/link";
import { redirect } from "next/navigation";
import { EspaceSocialLinks } from "@/components/espace/EspaceSocialLinks";
import { FlipPdfReader } from "@/components/FlipPdfReader";
import { entretienFlipReady } from "@/lib/entretien";
import { readCatalog } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function EntretienReaderPage() {
  const catalog = await readCatalog();
  if (!entretienFlipReady(catalog)) {
    if (catalog.entretienHref) {
      redirect(catalog.entretienHref);
    }
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[#2a211c] px-4 text-center text-white">
        <p className="font-display text-2xl">Guide d’entretien indisponible</p>
        <p className="max-w-md text-sm text-white/70">
          Aucun feuilletage n’est prêt. Uploadez un PDF ou une image dans
          l’admin Entretien.
        </p>
        <Link
          href="/espace"
          className="rounded-full bg-white/15 px-4 py-2 text-sm font-bold hover:bg-white/25"
        >
          Retour à l’espace
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[#2a211c]">
      <header className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3 text-white sm:px-6">
        <div className="min-w-0">
          <p className="text-[0.65rem] font-semibold tracking-[0.12em] text-white/60 uppercase">
            Conseils
          </p>
          <h1 className="truncate font-display text-xl font-semibold">
            Entretien de vos moules
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <EspaceSocialLinks variant="dark" />
          <Link
            href="/espace"
            className="rounded-full bg-white/15 px-4 py-2 text-sm font-bold hover:bg-white/25"
          >
            Espace
          </Link>
        </div>
      </header>
      <FlipPdfReader
        pagesBaseUrl="/api/entretien/pages"
        pageCount={catalog.entretienFlipPageCount!}
        title="Entretien de vos moules"
      />
    </div>
  );
}
