import Link from "next/link";

export const dynamic = "force-dynamic";

const MESSAGES: Record<string, { title: string; body: string }> = {
  used: {
    title: "Lien déjà utilisé",
    body: "Ce lien d’accès personnel a déjà été ouvert. Connectez-vous sur le site avec le mot de passe commun que vous avez noté à l’activation (téléphone, tablette ou autre navigateur).",
  },
  expired: {
    title: "Lien expiré",
    body: "Ce lien n’est plus valable (validité 14 jours). Demandez une nouvelle invitation à Yasmina.",
  },
  invalid: {
    title: "Lien invalide",
    body: "Ce lien d’accès n’est pas reconnu. Vérifiez l’adresse ou demandez une nouvelle invitation.",
  },
  rate: {
    title: "Trop de tentatives",
    body: "Veuillez réessayer dans quelques minutes.",
  },
};

type Props = { searchParams: Promise<{ r?: string }> };

export default async function AccesInvalidePage({ searchParams }: Props) {
  const { r } = await searchParams;
  const msg = MESSAGES[r || ""] ?? MESSAGES.invalid!;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-lg flex-col justify-center px-4 py-10">
      <div className="rounded-[1.75rem] bg-white px-7 py-9 shadow-[0_18px_50px_rgba(59,42,36,0.12)] sm:px-9">
        <p className="text-[0.7rem] font-semibold tracking-[0.14em] text-[#8b5a3c] uppercase">
          Accès
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold text-[#3b2a24]">
          {msg.title}
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-[#6a534a]">{msg.body}</p>
        <Link
          href="/"
          className="mt-8 flex h-12 w-full items-center justify-center rounded-full bg-[#8b5a3c] text-sm font-bold text-white transition hover:bg-[#6f452e]"
        >
          Aller à la connexion
        </Link>
      </div>
    </main>
  );
}
