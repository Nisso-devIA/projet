"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type InviteRow = {
  id: string;
  name: string;
  email: string;
  sentAt: string;
};

export function InviteClientForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [invites, setInvites] = useState<InviteRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/admin/invites");
    if (!res.ok) return;
    const data = (await res.json()) as {
      configured?: boolean;
      invites?: InviteRow[];
    };
    setConfigured(Boolean(data.configured));
    setInvites(data.invites ?? []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), email: email.trim() }),
      });
      const data = (await res.json()) as {
        error?: string;
      };
      if (!res.ok) throw new Error(data.error || "Envoi échoué");
      setEmail("");
      setName("");
      setMessage("Mail d’accès envoyé.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function removeInvite(id: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/invites", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      const data = (await res.json()) as { error?: string };
      if (!res.ok) throw new Error(data.error || "Suppression échouée");
      setMessage("Entrée retirée de l’historique.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function clearHistory() {
    if (
      !window.confirm(
        "Effacer tout l’historique des envois (e-mails) ? Cette action est définitive.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/invites", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clearAll: true }),
      });
      const data = (await res.json()) as { error?: string };
      if (!res.ok) throw new Error(data.error || "Suppression échouée");
      setMessage("Historique des envois effacé.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl bg-[#f3e6d4]/90 p-5 sm:p-6">
      <h2 className="font-display text-2xl font-semibold">
        Mail d’accès automatique
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
        Après une commande sur{" "}
        <span className="font-medium text-ink">
          boutique.guydemarle.com/?s=miinapatisserie5
        </span>
        , copiez le prénom et l’e-mail depuis l’espace conseillère Guy Demarle.
        Le mail part depuis la boîte pro avec un{" "}
        <span className="font-medium text-ink">lien d’accès unique</span> (une
        seule utilisation). Le mot de passe commun n’est plus dans le mail : il
        s’affiche une fois à l’activation du lien.
      </p>

      {configured === false ? (
        <p className="mt-3 rounded-xl bg-red-100 px-4 py-3 text-sm font-medium text-danger">
          Envoi non configuré : il manque RESEND_API_KEY (même clé que le site
          recettes).
        </p>
      ) : null}

      {(message || error) && (
        <p
          className={`mt-3 rounded-xl px-4 py-3 text-sm font-medium ${
            error ? "bg-red-100 text-danger" : "bg-emerald-100 text-emerald-900"
          }`}
        >
          {error || message}
        </p>
      )}

      <form
        onSubmit={onSubmit}
        className="mt-4 grid gap-3 sm:grid-cols-[1fr_1.2fr_auto]"
      >
        <label className="flex flex-col gap-1 text-sm font-medium">
          Prénom
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Camille"
            autoComplete="off"
            className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          E-mail de la cliente
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="camille@email.fr"
            autoComplete="off"
            className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
          />
        </label>
        <button
          type="submit"
          disabled={busy || configured === false}
          className="mt-auto h-[42px] rounded-full bg-accent px-5 text-sm font-bold text-white hover:bg-accent-strong disabled:opacity-50"
        >
          {busy ? "Envoi…" : "Envoyer l’accès"}
        </button>
      </form>

      {invites.length > 0 ? (
        <div className="mt-5 border-t border-ink/10 pt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
              Derniers envois
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void clearHistory()}
              className="text-xs font-semibold text-danger hover:underline disabled:opacity-50"
            >
              Tout effacer
            </button>
          </div>
          <ul className="flex max-h-80 flex-col gap-1.5 overflow-auto">
            {invites.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white/70 px-3 py-1.5 text-sm"
              >
                <span className="min-w-0 font-medium">
                  {item.name || "—"}{" "}
                  <span className="font-normal text-ink-soft">{item.email}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="text-[0.7rem] text-ink-soft">
                    {new Date(item.sentAt).toLocaleString("fr-FR")}
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void removeInvite(item.id)}
                    className="rounded-full border border-danger/40 bg-white px-2.5 py-0.5 text-xs font-bold text-danger hover:bg-danger/10 disabled:opacity-50"
                    aria-label={`Supprimer ${item.email} de l’historique`}
                  >
                    Supprimer
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
