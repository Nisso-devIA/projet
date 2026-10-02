"use client";

import { FormEvent, useState } from "react";

export function ContactForm({ email }: { email: string }) {
  const [status, setStatus] = useState<"idle" | "sent">("idle");

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const name = String(data.get("name") || "");
    const userEmail = String(data.get("email") || "");
    const message = String(data.get("message") || "");
    const subject = encodeURIComponent(`Contact Wado-Osny — ${name}`);
    const body = encodeURIComponent(
      `Nom : ${name}\nEmail : ${userEmail}\n\n${message}`,
    );
    window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
    setStatus("sent");
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="grid gap-5 md:grid-cols-2">
        <label className="block">
          <span className="text-xs uppercase tracking-[0.18em] text-paper-muted">
            Nom *
          </span>
          <input
            required
            name="name"
            className="mt-2 w-full rounded-sm border border-line bg-ink-lift px-4 py-3 text-paper outline-none transition focus:border-crimson-bright"
          />
        </label>
        <label className="block">
          <span className="text-xs uppercase tracking-[0.18em] text-paper-muted">
            Email *
          </span>
          <input
            required
            type="email"
            name="email"
            className="mt-2 w-full rounded-sm border border-line bg-ink-lift px-4 py-3 text-paper outline-none transition focus:border-crimson-bright"
          />
        </label>
      </div>
      <label className="block">
        <span className="text-xs uppercase tracking-[0.18em] text-paper-muted">
          Message *
        </span>
        <textarea
          required
          name="message"
          rows={6}
          className="mt-2 w-full resize-y rounded-sm border border-line bg-ink-lift px-4 py-3 text-paper outline-none transition focus:border-crimson-bright"
        />
      </label>
      <label className="flex items-start gap-3 text-sm text-paper-muted">
        <input
          required
          type="checkbox"
          className="mt-1 accent-crimson"
        />
        <span>
          J&apos;accepte la{" "}
          <a href="/confidentialite" className="text-gold underline-offset-2 hover:underline">
            politique de confidentialité
          </a>
          .
        </span>
      </label>
      <button
        type="submit"
        className="rounded-sm bg-crimson px-6 py-3 text-sm font-medium text-paper transition hover:bg-crimson-bright"
      >
        Envoyer
      </button>
      {status === "sent" ? (
        <p className="text-sm text-gold">
          Ouverture de votre client mail… Vous pouvez aussi écrire à{" "}
          <a className="underline" href={`mailto:${email}`}>
            {email}
          </a>
          .
        </p>
      ) : null}
    </form>
  );
}
