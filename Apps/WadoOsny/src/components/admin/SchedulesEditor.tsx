"use client";

import { useActionState, useState } from "react";
import type { Schedules } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

function slotsToText(
  slots: { day: string; time: string; place: string }[],
) {
  return slots.map((s) => `${s.day} | ${s.time} | ${s.place}`).join("\n");
}

function textToSlots(text: string) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [day = "", time = "", place = ""] = line.split("|").map((p) => p.trim());
      return { day, time, place };
    });
}

export function SchedulesEditor({
  action,
  initial,
}: {
  action: Action;
  initial: Schedules;
}) {
  const [kids, setKids] = useState(initial.kids);
  const [adults, setAdults] = useState(initial.adults);
  const [state, formAction, pending] = useActionState(action, null);

  return (
    <form
      action={(fd) => {
        fd.set(
          "payload",
          JSON.stringify({
            kids: kids.map((g) => ({
              ...g,
              slots: textToSlots(
                (document.getElementById(`kids-${g.id}`) as HTMLTextAreaElement)
                  ?.value ?? "",
              ),
            })),
            adults: adults.map((g) => ({
              ...g,
              slots: textToSlots(
                (
                  document.getElementById(`adults-${g.id}`) as HTMLTextAreaElement
                )?.value ?? "",
              ),
            })),
          }),
        );
        return formAction(fd);
      }}
    >
      {state?.error ? <p className="admin-error">{state.error}</p> : null}

      <h2 className="font-display text-2xl mb-4">Enfants</h2>
      {kids.map((g, i) => (
        <div key={g.id} className="admin-card">
          <div className="admin-grid-2">
            <div className="admin-field">
              <label>Groupe</label>
              <input
                value={g.group}
                onChange={(e) => {
                  const next = [...kids];
                  next[i] = { ...g, group: e.target.value };
                  setKids(next);
                }}
              />
            </div>
            <div className="admin-field">
              <label>Âges</label>
              <input
                value={g.ages}
                onChange={(e) => {
                  const next = [...kids];
                  next[i] = { ...g, ages: e.target.value };
                  setKids(next);
                }}
              />
            </div>
          </div>
          <div className="admin-field">
            <label>Focus</label>
            <textarea
              value={g.focus}
              onChange={(e) => {
                const next = [...kids];
                next[i] = { ...g, focus: e.target.value };
                setKids(next);
              }}
            />
          </div>
          <div className="admin-field">
            <label>Créneaux (Jour | Horaire | Lieu)</label>
            <textarea
              id={`kids-${g.id}`}
              defaultValue={slotsToText(g.slots)}
              rows={4}
            />
          </div>
        </div>
      ))}

      <h2 className="font-display text-2xl mb-4 mt-8">Adultes</h2>
      {adults.map((g, i) => (
        <div key={g.id} className="admin-card">
          <div className="admin-field">
            <label>Titre</label>
            <input
              value={g.title}
              onChange={(e) => {
                const next = [...adults];
                next[i] = { ...g, title: e.target.value };
                setAdults(next);
              }}
            />
          </div>
          <div className="admin-field">
            <label>Description</label>
            <textarea
              value={g.description}
              onChange={(e) => {
                const next = [...adults];
                next[i] = { ...g, description: e.target.value };
                setAdults(next);
              }}
            />
          </div>
          <div className="admin-field">
            <label>Créneaux (Jour | Horaire | Lieu)</label>
            <textarea
              id={`adults-${g.id}`}
              defaultValue={slotsToText(g.slots)}
              rows={4}
            />
          </div>
        </div>
      ))}

      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : "Enregistrer les horaires"}
      </button>
    </form>
  );
}
