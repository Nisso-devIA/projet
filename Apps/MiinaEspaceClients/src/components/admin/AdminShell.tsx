"use client";

import {
  AdminPasswordExpiryPopup,
  type PasswordExpiryInfo,
} from "@/components/admin/AdminPasswordExpiryPopup";

type Props = {
  title: string;
  active: "moules" | "mail" | "entretien";
  children: React.ReactNode;
  passwordExpiry?: PasswordExpiryInfo | null;
};

const tabClass = (on: boolean) =>
  `rounded-full px-4 py-2 text-sm font-semibold ${
    on
      ? "bg-accent text-white"
      : "border border-ink/20 bg-white/70 hover:bg-white"
  }`;

export function AdminShell({ title, active, children, passwordExpiry }: Props) {
  async function logout() {
    await fetch("/api/admin/logout", { method: "POST" });
    window.location.href = "/miina-admin/login";
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6">
      <AdminPasswordExpiryPopup info={passwordExpiry} />
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold tracking-[0.12em] text-ink-soft uppercase">
            Administration
          </p>
          <h1 className="font-display text-3xl font-semibold">{title}</h1>
        </div>
        <nav className="flex flex-wrap gap-2" aria-label="Sections admin">
          <a href="/miina-admin" className={tabClass(active === "moules")}>
            Moules
          </a>
          <a
            href="/miina-admin/entretien"
            className={tabClass(active === "entretien")}
          >
            Entretien
          </a>
          <a href="/miina-admin/mail" className={tabClass(active === "mail")}>
            Mail
          </a>
          <a
            href="/miina-admin/change-password"
            className="rounded-full border border-ink/20 bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white"
          >
            Mot de passe
          </a>
          <a
            href="/espace"
            className="rounded-full border border-ink/20 bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white"
          >
            Voir l’espace
          </a>
          <button
            type="button"
            onClick={logout}
            className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-white hover:bg-accent-strong"
          >
            Déconnexion
          </button>
        </nav>
      </header>
      {children}
    </div>
  );
}
