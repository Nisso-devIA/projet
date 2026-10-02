import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_COOKIE, sitePassword, verifySession } from "@/lib/auth";
import { verifyPasswordReveal } from "@/lib/invites";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{ e?: string; s?: string }>;
};

export default async function AccesBienvenuePage({ searchParams }: Props) {
  const jar = await cookies();
  const ok = await verifySession(jar.get(AUTH_COOKIE)?.value);
  if (!ok) redirect("/");

  const { e, s } = await searchParams;
  const canReveal = Boolean(e && s && verifyPasswordReveal(e, s));
  const password = canReveal ? sitePassword() : null;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-lg flex-col justify-center px-4 py-10">
      <div className="rounded-[1.75rem] bg-white px-7 py-9 shadow-[0_18px_50px_rgba(59,42,36,0.12)] sm:px-9">
        <p className="text-[0.7rem] font-semibold tracking-[0.14em] text-[#8b5a3c] uppercase">
          Accès activé
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold text-[#3b2a24]">
          Bienvenue dans l’espace recettes
        </h1>

        {password ? (
          <>
            <p className="mt-4 text-sm leading-relaxed text-[#6a534a]">
              Notez ce mot de passe commun : il vous servira pour vous reconnecter
              depuis un téléphone, une tablette ou un autre navigateur (ce lien
              mail ne fonctionne qu’une fois).
            </p>
            <p className="mt-5 rounded-xl border border-[#e4d8cc] bg-[#faf2e6] px-4 py-3 text-center font-mono text-lg font-semibold tracking-wide text-[#3b2a24]">
              {password}
            </p>
            <p className="mt-3 text-center text-xs text-[#8b5a3c]">
              Affiché une seule fois après l’activation du lien — notez-le
              maintenant.
            </p>
          </>
        ) : (
          <p className="mt-4 text-sm leading-relaxed text-[#6a534a]">
            Votre session est active. Si le mot de passe ne s’est pas affiché,
            demandez une nouvelle invitation à Yasmina (le lien mail ne
            fonctionne qu’une fois).
          </p>
        )}

        <Link
          href="/espace"
          className="mt-8 flex h-12 w-full items-center justify-center rounded-full bg-[#8b5a3c] text-sm font-bold text-white transition hover:bg-[#6f452e]"
        >
          Entrer dans l’espace
        </Link>
      </div>
    </main>
  );
}
