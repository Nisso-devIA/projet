"use client";

import { useEffect, useState } from "react";

export type PasswordExpiryInfo = {
  warnWithin48h: boolean;
  hoursLeft: number | null;
  expiresAt: string | null;
  updatedAt: string | null;
};

type Props = {
  info: PasswordExpiryInfo | null | undefined;
};

export function AdminPasswordExpiryPopup({ info }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!info?.warnWithin48h || info.hoursLeft == null) {
      setOpen(false);
      return;
    }
    const key = `miina_admin_pwd_warn_${info.updatedAt ?? "x"}`;
    try {
      if (sessionStorage.getItem(key) === "1") {
        setOpen(false);
        return;
      }
    } catch {
      /* ignore */
    }
    setOpen(true);
  }, [info]);

  function dismiss() {
    setOpen(false);
    if (info?.updatedAt) {
      try {
        sessionStorage.setItem(`miina_admin_pwd_warn_${info.updatedAt}`, "1");
      } catch {
        /* ignore */
      }
    }
  }

  if (!open || !info?.warnWithin48h || info.hoursLeft == null) return null;

  const hours = Math.max(1, Math.ceil(info.hoursLeft));
  const when =
    hours <= 24
      ? `dans environ ${hours} heure${hours > 1 ? "s" : ""}`
      : `dans moins de 48 heures`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pwd-expiry-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-[#faf2e6] p-6 shadow-xl">
        <p className="text-[0.7rem] font-semibold tracking-[0.12em] text-ink-soft uppercase">
          Sécurité
        </p>
        <h2
          id="pwd-expiry-title"
          className="font-display mt-1 text-2xl font-semibold text-ink"
        >
          Mot de passe bientôt expiré
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          Votre mot de passe admin expire {when}. Modifiez-le maintenant pour
          éviter un blocage à la prochaine connexion.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <a
            href="/miina-admin/change-password"
            className="rounded-full bg-accent px-4 py-2.5 text-sm font-bold text-white hover:bg-accent-strong"
          >
            Changer le mot de passe
          </a>
          <button
            type="button"
            onClick={dismiss}
            className="rounded-full border border-ink/20 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-white/80"
          >
            Plus tard
          </button>
        </div>
      </div>
    </div>
  );
}
