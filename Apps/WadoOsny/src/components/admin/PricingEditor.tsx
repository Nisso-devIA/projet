"use client";

import { useActionState, useState } from "react";
import type { PricingPlan } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

export function PricingEditor({
  action,
  initial,
}: {
  action: Action;
  initial: PricingPlan[];
}) {
  const [plans, setPlans] = useState(initial);
  const [state, formAction, pending] = useActionState(action, null);

  return (
    <form
      action={(fd) => {
        fd.set("payload", JSON.stringify(plans));
        return formAction(fd);
      }}
    >
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      {plans.map((plan, i) => (
        <div key={plan.id} className="admin-card">
          <div className="admin-field">
            <label>Titre</label>
            <input
              value={plan.title}
              onChange={(e) => {
                const next = [...plans];
                next[i] = { ...plan, title: e.target.value };
                setPlans(next);
              }}
            />
          </div>
          <div className="admin-grid-2">
            <div className="admin-field">
              <label>Cotisation club (€)</label>
              <input
                type="number"
                value={plan.club}
                onChange={(e) => {
                  const next = [...plans];
                  next[i] = { ...plan, club: Number(e.target.value) };
                  setPlans(next);
                }}
              />
            </div>
            <div className="admin-field">
              <label>Licence (€, vide = aucune)</label>
              <input
                type="number"
                value={plan.license ?? ""}
                onChange={(e) => {
                  const next = [...plans];
                  const v = e.target.value;
                  next[i] = {
                    ...plan,
                    license: v === "" ? null : Number(v),
                  };
                  setPlans(next);
                }}
              />
            </div>
          </div>
          <div className="admin-field">
            <label>Note</label>
            <textarea
              value={plan.note}
              onChange={(e) => {
                const next = [...plans];
                next[i] = { ...plan, note: e.target.value };
                setPlans(next);
              }}
            />
          </div>
        </div>
      ))}
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : "Enregistrer les tarifs"}
      </button>
    </form>
  );
}
