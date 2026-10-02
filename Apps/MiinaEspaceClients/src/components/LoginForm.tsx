"use client";

import Image from "next/image";
import { FormEvent, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  passwordInputProps,
  postPasswordJson,
} from "@/lib/password-input";

export function LoginForm() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, startTransition] = useTransition();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = event.currentTarget;
    const password = String(new FormData(form).get("password") || "");
    startTransition(async () => {
      try {
        const res = await postPasswordJson("/api/auth", { password });
        // Efface le champ dès l’envoi (réduit la fenêtre d’exposition DOM)
        form.reset();
        setShowPassword(false);
        if (!res.ok) {
          const data = (await res.json().catch(() => null)) as {
            error?: string;
          } | null;
          setError(
            data?.error ||
              (res.status === 429
                ? "Trop de tentatives. Réessayez plus tard."
                : "Mot de passe incorrect."),
          );
          return;
        }
        router.replace("/espace");
        router.refresh();
      } catch {
        form.reset();
        setShowPassword(false);
        setError("Connexion impossible.");
      }
    });
  }

  return (
    <form
      ref={formRef}
      onSubmit={onSubmit}
      method="post"
      autoComplete="on"
      className="w-full max-w-[22.5rem] rounded-[1.75rem] bg-white px-7 py-8 shadow-[0_18px_50px_rgba(59,42,36,0.12)] sm:max-w-md sm:px-9 sm:py-10"
    >
      <div className="mb-5 flex flex-col items-center">
        <Image
          src="/brand/logo-connexion.png"
          alt="Miina Pâtisserie"
          width={1792}
          height={1008}
          className="mb-2 h-auto w-full max-w-[16rem] object-contain sm:max-w-[18rem]"
          priority
        />
        <p className="mt-2 max-w-[16.5rem] text-center text-[0.82rem] leading-relaxed text-[#6a534a]">
          Accès réservé à mes clients Guy Demarle. Merci de ne pas partager le
          lien ni le mot de passe.
        </p>
      </div>

      <label
        htmlFor="password"
        className="mb-2 block text-sm font-semibold text-[#3b2a24]"
      >
        Mot de passe
      </label>
      <div className="relative mb-4">
        <input
          id="password"
          name="password"
          {...passwordInputProps}
          type={showPassword ? "text" : "password"}
          required
          disabled={pending}
          className="h-12 w-full rounded-xl border border-[#e4d8cc] bg-white px-3.5 pr-14 text-[#3b2a24] outline-none focus:border-[#8b5a3c]"
        />
        <button
          type="button"
          onClick={() => setShowPassword((v) => !v)}
          disabled={pending}
          className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-semibold text-[#8b5a3c] hover:bg-[#f7efe6] disabled:opacity-70"
          aria-label={
            showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"
          }
          aria-pressed={showPassword}
        >
          {showPassword ? "Masquer" : "Voir"}
        </button>
      </div>
      {error ? <p className="mb-3 text-sm text-danger">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="h-12 w-full rounded-full bg-[#8b5a3c] text-sm font-bold text-white transition hover:bg-[#6f452e] disabled:opacity-70"
      >
        {pending ? "Vérification…" : "Entrer dans l'espace"}
      </button>

      <p className="font-display mt-7 text-center text-[0.8rem] text-[#8b5a3c] italic">
        Recettes gourmandes · simples · faites avec amour
      </p>
    </form>
  );
}
