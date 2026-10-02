"use client";

import { FormEvent, useRef, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import type { PasswordExpiryInfo } from "@/components/admin/AdminPasswordExpiryPopup";

type Props = {
  initialHref: string;
  initialFlipPageCount?: number;
  initialOriginalName?: string;
  passwordExpiry?: PasswordExpiryInfo | null;
};

export function AdminEntretien({
  initialHref,
  initialFlipPageCount = 0,
  initialOriginalName = "",
  passwordExpiry,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [href, setHref] = useState(initialHref);
  const [pages, setPages] = useState(initialFlipPageCount);
  const [originalName, setOriginalName] = useState(initialOriginalName);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function uploadFile(list: FileList | null) {
    const file = list?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/admin/entretien", {
        method: "POST",
        body: form,
      });
      const data = (await res.json()) as {
        error?: string;
        entretienFlipPageCount?: number;
        entretienOriginalName?: string;
      };
      if (!res.ok) throw new Error(data.error || "Upload impossible");
      setPages(data.entretienFlipPageCount ?? 0);
      setOriginalName(data.entretienOriginalName || file.name);
      setMessage(
        `Feuilletage prêt (${data.entretienFlipPageCount ?? 0} page${
          (data.entretienFlipPageCount ?? 0) > 1 ? "s" : ""
        })`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function clearFile() {
    if (!confirm("Retirer le guide uploadé ? Le lien FlipHTML5 de secours sera utilisé.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/entretien", { method: "DELETE" });
      const data = (await res.json()) as { error?: string };
      if (!res.ok) throw new Error(data.error || "Erreur");
      setPages(0);
      setOriginalName("");
      setMessage("Guide retiré — secours FlipHTML5");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function saveHref(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/entretien", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entretienHref: href.trim() }),
      });
      const data = (await res.json()) as {
        error?: string;
        entretienHref?: string;
      };
      if (!res.ok) throw new Error(data.error || "Erreur");
      setHref(data.entretienHref || href.trim());
      setMessage("Lien de secours enregistré");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell
      title="Entretien des moules"
      active="entretien"
      passwordExpiry={passwordExpiry}
    >
      {(message || error) && (
        <p
          className={`rounded-xl px-4 py-3 text-sm font-medium ${
            error ? "bg-red-100 text-danger" : "bg-emerald-100 text-emerald-900"
          }`}
        >
          {error || message}
        </p>
      )}

      <section className="rounded-2xl bg-[#f3e6d4]/90 p-5 sm:p-6">
        <h2 className="font-display text-xl font-semibold">
          Guide (feuilletage)
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Comme pour les recettes : upload PDF ou image → feuilletage. La
          bannière de l’espace reste{" "}
          <span className="font-semibold">/brand/entretien-v8.png</span> ; le clic
          ouvre le guide.
        </p>
        <div className="mt-4 flex flex-col gap-3">
          <img
            src="/brand/entretien-v8.png"
            alt="Bannière espace clients"
            className="mx-auto h-auto max-h-28 w-full max-w-xl object-contain"
          />
          <p className="text-xs text-ink-soft">
            Aperçu de la bannière (fixe) sur l’espace clients.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,image/png,image/jpeg,image/webp,image/gif,image/tiff,.pdf,.png,.jpg,.jpeg,.webp,.gif,.tif,.tiff"
            disabled={busy}
            onChange={(e) => uploadFile(e.target.files)}
            className="text-sm font-normal file:mr-3 file:rounded-full file:border-0 file:bg-card file:px-3 file:py-1 file:text-xs file:font-bold"
          />
          <p className="text-xs text-ink-soft">
            PDF ou image — max 40&nbsp;Mo. Génération du feuilletage à
            l’upload.
          </p>
          {pages > 0 ? (
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <p className="font-medium text-ink">
                Prêt : {originalName || "guide"} · {pages} page
                {pages > 1 ? "s" : ""}
              </p>
              <a
                href="/espace/entretien"
                className="text-xs font-semibold text-accent underline"
              >
                Voir le feuilletage
              </a>
              <button
                type="button"
                disabled={busy}
                onClick={clearFile}
                className="text-xs font-semibold text-danger hover:underline disabled:opacity-50"
              >
                Retirer
              </button>
            </div>
          ) : (
            <p className="text-xs text-ink-soft">
              Aucun guide uploadé — clic = lien FlipHTML5 de secours.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-2xl bg-[#f3e6d4]/90 p-5 sm:p-6">
        <h2 className="font-display text-xl font-semibold">
          Lien FlipHTML5 (secours)
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Utilisé seulement s’il n’y a pas de feuilletage prêt.
        </p>
        <form onSubmit={saveHref} className="mt-4 flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm font-medium">
            URL de secours
            <input
              value={href}
              onChange={(e) => setHref(e.target.value)}
              placeholder="https://online.fliphtml5.com/…"
              className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="self-start rounded-full bg-accent px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            Enregistrer le lien de secours
          </button>
        </form>
      </section>
    </AdminShell>
  );
}
