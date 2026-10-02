"use client";

import { useActionState } from "react";
import type { ClubInfo } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

export function ClubForm({
  action,
  club,
}: {
  action: Action;
  club: ClubInfo;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  return (
    <form action={formAction} className="admin-card">
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <input type="hidden" name="locCount" value={club.locations.length} />
      <div className="admin-grid-2">
        <div className="admin-field">
          <label>Nom court</label>
          <input name="name" defaultValue={club.name} required />
        </div>
        <div className="admin-field">
          <label>Nom complet</label>
          <input name="fullName" defaultValue={club.fullName} required />
        </div>
      </div>
      <div className="admin-field">
        <label>Accroche</label>
        <input name="tagline" defaultValue={club.tagline} />
      </div>
      <div className="admin-grid-2">
        <div className="admin-field">
          <label>Email</label>
          <input name="email" type="email" defaultValue={club.email} required />
        </div>
        <div className="admin-field">
          <label>RNA</label>
          <input name="rna" defaultValue={club.rna} />
        </div>
      </div>
      <div className="admin-field">
        <label>Association</label>
        <input name="association" defaultValue={club.association} />
      </div>
      <div className="admin-field">
        <label>Siège</label>
        <input name="siege" defaultValue={club.siege} />
      </div>
      <div className="admin-field">
        <label>Image plan (chemin)</label>
        <input name="mapImage" defaultValue={club.mapImage} />
      </div>
      <div className="admin-field">
        <label>Lien Google Maps principal</label>
        <input name="mapLink" defaultValue={club.mapLink} />
      </div>

      <h2 className="text-xl mt-6 mb-3">Lieux</h2>
      {club.locations.map((loc, i) => (
        <div key={i} className="mb-4 border-t border-line pt-4">
          <p className="admin-meta mb-2">Lieu {i + 1}</p>
          <div className="admin-field">
            <label>Nom</label>
            <input name={`loc_name_${i}`} defaultValue={loc.name} />
          </div>
          <div className="admin-field">
            <label>Court</label>
            <input name={`loc_short_${i}`} defaultValue={loc.short} />
          </div>
          <div className="admin-field">
            <label>Adresse</label>
            <input name={`loc_address_${i}`} defaultValue={loc.address} />
          </div>
          <div className="admin-field">
            <label>Ville</label>
            <input name={`loc_city_${i}`} defaultValue={loc.city} />
          </div>
          <div className="admin-field">
            <label>Lien Maps</label>
            <input name={`loc_maps_${i}`} defaultValue={loc.mapsUrl} />
          </div>
        </div>
      ))}

      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : "Enregistrer"}
      </button>
    </form>
  );
}
