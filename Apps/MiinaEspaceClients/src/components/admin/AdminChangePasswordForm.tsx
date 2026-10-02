"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  newPasswordInputProps,
  passwordInputProps,
  postPasswordJson,
} from "@/lib/password-input";

type Props = {
  forced?: boolean;
  maxAgeDays?: number;
};

export function AdminChangePasswordForm({
  forced = false,
  maxAgeDays = 90,
}: Props) {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "code">("form");
  const [code, setCode] = useState("");
  const [maskedTo, setMaskedTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onRequestCode(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const form = e.currentTarget;
    const fd = new FormData(form);
    const currentPassword = String(fd.get("currentPassword") || "");
    const newPassword = String(fd.get("newPassword") || "");
    const confirmPassword = String(fd.get("confirmPassword") || "");
    try {
      const res = await postPasswordJson("/api/admin/change-password", {
        action: "request",
        currentPassword,
        newPassword,
        confirmPassword,
      });
      form.reset();
      const data = (await res.json().catch(() => null)) as {
        error?: string;
        codeSent?: boolean;
        maskedTo?: string;
      } | null;
      if (!res.ok) {
        setError(data?.error || "Impossible d’envoyer le code");
        setPending(false);
        return;
      }
      setMaskedTo(data?.maskedTo ?? null);
      setStep("code");
      setPending(false);
    } catch {
      form.reset();
      setError("Connexion impossible");
      setPending(false);
    }
  }

  async function onConfirmCode(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const res = await postPasswordJson("/api/admin/change-password", {
        action: "confirm",
        code,
      });
      const data = (await res.json().catch(() => null)) as {
        error?: string;
      } | null;
      if (!res.ok) {
        setError(data?.error || "Code incorrect");
        setPending(false);
        return;
      }
      setCode("");
      router.replace("/miina-admin");
      router.refresh();
    } catch {
      setError("Connexion impossible");
      setPending(false);
    }
  }

  async function onCancel() {
    setPending(true);
    setError(null);
    try {
      await postPasswordJson("/api/admin/change-password", {
        action: "cancel",
      });
    } catch {
      /* ignore */
    }
    setStep("form");
    setCode("");
    setMaskedTo(null);
    setPending(false);
  }

  if (step === "code") {
    return (
      <form
        onSubmit={onConfirmCode}
        method="post"
        autoComplete="off"
        className="mx-auto flex w-full max-w-md flex-col gap-4 rounded-2xl bg-[#f3e6d4]/90 px-6 py-8 shadow-sm"
      >
        <div>
          <p className="text-[0.7rem] font-semibold tracking-[0.14em] text-ink-soft uppercase">
            Sécurité admin
          </p>
          <h1 className="font-display text-3xl font-semibold text-ink">
            Code de confirmation
          </h1>
          <p className="mt-2 text-sm text-ink-soft">
            Un code à 6 chiffres a été envoyé
            {maskedTo ? (
              <>
                {" "}
                à <strong>{maskedTo}</strong>
              </>
            ) : null}
            . Valable 15 minutes.
          </p>
        </div>

        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Code
          <input
            type="text"
            name="code"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(e) =>
              setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
            }
            className="rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-base font-normal tracking-[0.3em] outline-none focus:border-accent"
            required
          />
        </label>

        {error ? <p className="text-sm font-medium text-danger">{error}</p> : null}

        <button
          type="submit"
          disabled={pending || code.length !== 6}
          className="rounded-full bg-accent px-4 py-2.5 text-sm font-bold text-white hover:bg-accent-strong disabled:opacity-60"
        >
          {pending ? "Vérification…" : "Confirmer le changement"}
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={onCancel}
          className="rounded-full border border-ink/20 px-4 py-2.5 text-sm font-semibold text-ink hover:bg-white/60 disabled:opacity-60"
        >
          Annuler et recommencer
        </button>
      </form>
    );
  }

  return (
    <form
      onSubmit={onRequestCode}
      method="post"
      autoComplete="on"
      className="mx-auto flex w-full max-w-md flex-col gap-4 rounded-2xl bg-[#f3e6d4]/90 px-6 py-8 shadow-sm"
    >
      <div>
        <p className="text-[0.7rem] font-semibold tracking-[0.14em] text-ink-soft uppercase">
          Sécurité admin
        </p>
        <h1 className="font-display text-3xl font-semibold text-ink">
          {forced ? "Changement obligatoire" : "Nouveau mot de passe"}
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          {forced
            ? `Première connexion ou mot de passe expiré (${maxAgeDays} jours). Un code e-mail à 6 chiffres confirmera le changement.`
            : `Le mot de passe admin expire tous les ${maxAgeDays} jours. Un code de confirmation sera envoyé par e-mail (15 min).`}
        </p>
      </div>

      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Mot de passe actuel
        <input
          name="currentPassword"
          {...passwordInputProps}
          className="rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-base font-normal outline-none focus:border-accent"
          required
          disabled={pending}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Nouveau mot de passe
        <input
          name="newPassword"
          {...newPasswordInputProps}
          minLength={10}
          className="rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-base font-normal outline-none focus:border-accent"
          required
          disabled={pending}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Confirmer
        <input
          name="confirmPassword"
          {...newPasswordInputProps}
          minLength={10}
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
        {pending ? "Envoi du code…" : "Recevoir le code de confirmation"}
      </button>
    </form>
  );
}
