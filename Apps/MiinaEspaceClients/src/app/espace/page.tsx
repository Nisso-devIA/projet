import Image from "next/image";
import Link from "next/link";
import { logoutAction } from "@/app/actions";
import { EspaceSocialLinks } from "@/components/espace/EspaceSocialLinks";
import { WelcomeCard } from "@/components/WelcomeCard";
import { VoirRecettesButton } from "@/components/VoirRecettesButton";
import { entretienViewerHref } from "@/lib/entretien";
import { mouleViewerHref, readCatalog } from "@/lib/store";

export const dynamic = "force-dynamic";

export default async function EspacePage() {
  const catalog = await readCatalog();
  const entretienHref = entretienViewerHref(catalog);
  const entretienInternal = entretienHref.startsWith("/");

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 grid grid-cols-[auto_1fr_auto] items-center gap-3 border-b border-ink/10 bg-bg/75 px-4 py-3 backdrop-blur-md sm:gap-4 sm:px-6">
        <div className="min-w-0">
          <p className="text-[0.7rem] font-semibold tracking-[0.12em] text-ink-soft uppercase">
            Miina Pâtisserie
          </p>
          <p className="font-display text-xl font-semibold">Espace clients</p>
        </div>
        <p className="font-display hidden text-center text-[0.88rem] leading-snug font-bold text-ink sm:block sm:text-[0.95rem] md:text-[1.05rem]">
          Comme en cuisine, on ne s’arrête jamais&nbsp;: de nouvelles recettes et
          de nouveaux moules viennent enrichir cet espace.
        </p>
        <div className="flex items-center gap-2 justify-self-end">
          <EspaceSocialLinks />
          <form action={logoutAction}>
            <button
              type="submit"
              className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-white hover:bg-accent-strong"
            >
              Quitter
            </button>
          </form>
        </div>
      </header>
      <p className="border-b border-ink/10 bg-bg/75 px-4 py-2.5 text-center font-display text-[0.85rem] leading-snug font-bold text-ink sm:hidden">
        Comme en cuisine, on ne s’arrête jamais&nbsp;: de nouvelles recettes et
        de nouveaux moules viennent enrichir cet espace.
      </p>

      <main className="mx-auto flex w-full max-w-5xl flex-col items-center gap-10 px-4 py-10 sm:gap-12 sm:px-6">
        <WelcomeCard />

        {entretienInternal ? (
          <Link
            href={entretienHref}
            className="block w-full max-w-2xl transition hover:-translate-y-0.5"
          >
            <Image
              src="/brand/entretien-v8.png"
              alt="Conseils d'entretien de vos moules"
              width={1475}
              height={312}
              className="h-auto w-full"
            />
          </Link>
        ) : (
          <a
            href={entretienHref}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full max-w-2xl transition hover:-translate-y-0.5"
          >
            <Image
              src="/brand/entretien-v8.png"
              alt="Conseils d'entretien de vos moules"
              width={1475}
              height={312}
              className="h-auto w-full"
            />
          </a>
        )}

        <Image
          src="/brand/titre-moules.png"
          alt="Choisissez votre moule"
          width={1894}
          height={886}
          className="h-auto w-full max-w-xl"
        />

        <ul className="mx-auto grid w-full max-w-4xl list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 lg:gap-5">
          {catalog.moules.map((moule) => {
            const href = mouleViewerHref(moule);
            const internal = href.startsWith("/");
            return (
              <li key={moule.id}>
                <article className="flex h-full flex-col items-center rounded-[1.5rem] bg-card px-2.5 pb-3.5 pt-2.5 sm:px-3 sm:pb-4 sm:pt-3">
                  <div className="mb-1.5 flex h-28 w-full items-end justify-center sm:h-32 lg:h-36">
                    {moule.image ? (
                      <Image
                        src={moule.image}
                        alt={moule.title}
                        width={1100}
                        height={800}
                        className="max-h-full w-auto max-w-[86%] object-contain"
                      />
                    ) : (
                      <span className="text-sm text-ink-soft">Photo à venir</span>
                    )}
                  </div>
                  <h2 className="flex min-h-[2.5rem] items-center justify-center px-1 text-center text-[0.88rem] leading-snug font-bold text-ink sm:min-h-[2.75rem] sm:text-[0.95rem]">
                    {moule.title}
                  </h2>
                  <VoirRecettesButton
                    href={href}
                    external={!internal}
                    label={`${moule.title} — voir les recettes`}
                  />
                </article>
              </li>
            );
          })}
        </ul>
      </main>
    </div>
  );
}
