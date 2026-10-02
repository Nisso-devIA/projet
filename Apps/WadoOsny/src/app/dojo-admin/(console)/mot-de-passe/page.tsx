"use client";

import { useActionState } from "react";
import { changeAdminPassword } from "@/app/dojo-admin/actions";

export default function PasswordPage() {
  const [state, action, pending] = useActionState(changeAdminPassword, null);
  return (
    <>
      <h1 className="font-display text-3xl mb-6">Mot de passe</h1>
      <form action={action} className="admin-card max-w-md">
        {state?.error ? <p className="admin-error">{state.error}</p> : null}
        <div className="admin-field">
          <label htmlFor="currentPassword">Mot de passe actuel</label>
          <input
            id="currentPassword"
            name="currentPassword"
            type="password"
            autoComplete="current-password"
            required
          />
        </div>
        <div className="admin-field">
          <label htmlFor="newPassword">Nouveau (12+ car., lettre + chiffre)</label>
          <input
            id="newPassword"
            name="newPassword"
            type="password"
            autoComplete="new-password"
            required
          />
        </div>
        <div className="admin-field">
          <label htmlFor="confirmPassword">Confirmation</label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            required
          />
        </div>
        <button className="admin-btn" type="submit" disabled={pending}>
          {pending ? "Enregistrement…" : "Changer le mot de passe"}
        </button>
      </form>
    </>
  );
}
