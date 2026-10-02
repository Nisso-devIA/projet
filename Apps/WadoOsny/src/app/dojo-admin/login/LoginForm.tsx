"use client";

import { useActionState } from "react";
import { loginAdmin } from "@/app/dojo-admin/actions";

export function LoginForm() {
  const [state, action, pending] = useActionState(loginAdmin, null);
  return (
    <form action={action} className="admin-card">
      <h1 className="font-display text-2xl">Admin club</h1>
      <p className="admin-meta mt-2 mb-6">Wado-Osny — accès réservé</p>
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <div className="admin-field">
        <label htmlFor="password">Mot de passe</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </div>
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "Connexion…" : "Se connecter"}
      </button>
    </form>
  );
}
