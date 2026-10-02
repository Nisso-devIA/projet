"use client";

import { useActionState } from "react";
import type { Instructor } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

export function InstructorForm({
  action,
  person,
}: {
  action: Action;
  person?: Instructor;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  return (
    <form action={formAction}>
      {person ? <input type="hidden" name="id" value={person.id} /> : null}
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <div className="admin-field">
        <label>Nom</label>
        <input name="name" required defaultValue={person?.name ?? ""} />
      </div>
      <div className="admin-field">
        <label>Grades (un par ligne)</label>
        <textarea
          name="ranks"
          rows={4}
          defaultValue={person?.ranks.join("\n") ?? ""}
        />
      </div>
      <div className="admin-field">
        <label>Bio</label>
        <textarea name="bio" rows={6} defaultValue={person?.bio ?? ""} />
      </div>
      <div className="admin-field">
        <label>Photo {person?.image ? "(laisser vide pour garder)" : ""}</label>
        <input name="imageFile" type="file" accept="image/png,image/jpeg,image/webp" />
      </div>
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : person ? "Mettre à jour" : "Ajouter"}
      </button>
    </form>
  );
}
