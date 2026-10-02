"use client";

import { useActionState } from "react";
import { GALLERY_CATEGORIES, type GalleryItem } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

export function GalleryAddForm({ action }: { action: Action }) {
  const [state, formAction, pending] = useActionState(action, null);
  return (
    <form action={formAction}>
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <div className="admin-field">
        <label>Image</label>
        <input name="file" type="file" accept="image/png,image/jpeg,image/webp" required />
      </div>
      <div className="admin-grid-2">
        <div className="admin-field">
          <label>Légende</label>
          <input name="alt" placeholder="Description" />
        </div>
        <div className="admin-field">
          <label>Catégorie</label>
          <select name="category" defaultValue="Cours">
            {GALLERY_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "Envoi…" : "Ajouter"}
      </button>
    </form>
  );
}

export function GalleryEditForm({
  action,
  item,
}: {
  action: Action;
  item: GalleryItem;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  return (
    <form action={formAction}>
      <input type="hidden" name="id" value={item.id} />
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <div className="admin-grid-2">
        <div className="admin-field">
          <label>Légende</label>
          <input name="alt" defaultValue={item.alt} required />
        </div>
        <div className="admin-field">
          <label>Catégorie</label>
          <select name="category" defaultValue={item.category}>
            {GALLERY_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : "Mettre à jour"}
      </button>
    </form>
  );
}
