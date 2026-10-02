"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  passwordInputProps,
  postPasswordJson,
} from "@/lib/password-input";

export function AdminLoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const form = e.currentTarget;
    const password = String(new FormData(form).get("password") || "");
    try {
      const res = await postPasswordJson("/api/admin/login", { password });
      form.reset();
      const data = (await res.json().catch(() => null)) as {
        error?: string;
        mustChange?: boolean;
      } | null;
      if (!res.ok) {
        setError(data?.error || "Mot de passe incorrect");
        setPending(false);
        return;
      }
      router.replace(
        data?.mustChange ? "/miina-admin/change-password" : "/miina-admin",
      );
      router.refresh();
    } catch {
      form.reset();
      setError("Connexion impossible");
      setPending(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      method="post"
      autoComplete="on"
      className="mx-auto flex w-full max-w-sm flex-col gap-4 rounded-2xl bg-[#f3e6d4]/90 px-6 py-8 shadow-sm"
    >
      <div>
        <p className="text-[0.7rem] font-semibold tracking-[0.14em] text-ink-soft uppercase">
          Miina Pâtisserie
        </p>
        <h1 className="font-display text-3xl font-semibold text-ink">
          Admin recettes
        </h1>
        <p className="mt-1 text-sm text-ink-soft">
          Gérez les moules et fusionnez les PDF automatiquement.
        </p>
      </div>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Mot de passe admin
        <input
          name="password"
          {...passwordInputProps}
          className="rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-base font-normal outline-none focus:border-accent"
          required
          disabled={pending}
        />
      </label>
      {error ? <p className="text-sm font-medium text-danger">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-full bg-accent px-4 py-2.5 text-sm font-bold text-white hover:bg-accent-strong disabled:opacity-60"
      >
        {pending ? "Connexion…" : "Entrer"}
      </button>
    </form>
  );
}
