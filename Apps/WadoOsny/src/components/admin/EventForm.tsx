"use client";

import { useActionState, useEffect, useId, useRef, useState } from "react";
import type { ClubEvent } from "@/content/defaults";

type Action = (
  prev: { error?: string } | null,
  formData: FormData,
) => Promise<{ error?: string } | null>;

type Suggestion = {
  id: string;
  label: string;
};

function formatPhotonFeature(feature: {
  properties?: Record<string, string | number | undefined>;
}): string {
  const p = feature.properties ?? {};
  const housenumber = p.housenumber != null ? String(p.housenumber).trim() : "";
  const street = String(p.street || p.road || "").trim();
  const name = String(p.name || "").trim();

  // Ligne rue avec numéro (ex. "12 rue de Chars")
  let streetLine = "";
  if (housenumber && street) {
    streetLine = `${housenumber} ${street}`;
  } else if (housenumber && name) {
    streetLine = `${housenumber} ${name}`;
  } else if (street) {
    streetLine = street;
  }

  const city = String(
    p.city || p.town || p.village || p.municipality || "",
  ).trim();
  const postcode = p.postcode != null ? String(p.postcode).trim() : "";
  const locality = [postcode, city].filter(Boolean).join(" ");
  const state = String(p.state || p.county || "").trim();

  const parts: string[] = [];
  const seen = new Set<string>();
  const push = (value: string) => {
    const v = value.trim();
    if (!v) return;
    const key = v.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    parts.push(v);
  };

  // POI / bâtiment nommé, sauf s’il duplique déjà la rue
  if (
    name &&
    name.toLowerCase() !== street.toLowerCase() &&
    name.toLowerCase() !== streetLine.toLowerCase() &&
    !streetLine.toLowerCase().startsWith(name.toLowerCase())
  ) {
    push(name);
  }
  push(streetLine || name);
  push(locality);
  if (state && state.toLowerCase() !== city.toLowerCase()) push(state);

  return parts.join(", ");
}

async function searchPlaces(query: string): Promise<Suggestion[]> {
  const q = query.trim();
  if (q.length < 3) return [];

  const url = new URL("https://photon.komoot.io/api/");
  url.searchParams.set("q", q);
  url.searchParams.set("limit", "8");
  url.searchParams.set("lang", "fr");
  // Bbox France métropolitaine (+ Corse) pour prioriser les résultats FR
  url.searchParams.set("bbox", "-5.5,41.2,9.8,51.2");

  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) return [];

  const data = (await res.json()) as {
    features?: {
      properties?: Record<string, string | number | undefined>;
      geometry?: { coordinates?: number[] };
    }[];
  };

  const ranked = [...(data.features ?? [])].sort((a, b) => {
    const aHas = a.properties?.housenumber != null ? 0 : 1;
    const bHas = b.properties?.housenumber != null ? 0 : 1;
    return aHas - bHas;
  });

  const out: Suggestion[] = [];
  const seen = new Set<string>();
  for (const feature of ranked) {
    const p = feature.properties ?? {};
    const code = String(p.countrycode ?? "").toUpperCase();
    const country = String(p.country ?? "").toLowerCase();
    const isFrance =
      code === "FR" ||
      (!code &&
        (country.includes("france") ||
          country.includes("frankreich") ||
          country.includes("francia")));
    if (!isFrance) continue;

    const label = formatPhotonFeature(feature);
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    const coords = feature.geometry?.coordinates?.join(",") ?? label;
    out.push({ id: coords, label });
    if (out.length >= 6) break;
  }
  return out;
}

export function EventForm({
  action,
  event,
}: {
  action: Action;
  event?: ClubEvent;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  const listId = useId();
  const [place, setPlace] = useState(event?.place ?? "");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);

  useEffect(() => {
    const q = place.trim();
    if (q.length < 3) {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    const id = ++requestId.current;
    setLoading(true);
    const timer = window.setTimeout(() => {
      void searchPlaces(q)
        .then((items) => {
          if (requestId.current !== id) return;
          setSuggestions(items);
          setOpen(items.length > 0);
        })
        .catch(() => {
          if (requestId.current !== id) return;
          setSuggestions([]);
        })
        .finally(() => {
          if (requestId.current === id) setLoading(false);
        });
    }, 280);

    return () => window.clearTimeout(timer);
  }, [place]);

  useEffect(() => {
    function onPointerDown(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  return (
    <form action={formAction}>
      {event ? <input type="hidden" name="id" value={event.id} /> : null}
      {state?.error ? <p className="admin-error">{state.error}</p> : null}
      <div className="admin-grid-2">
        <div className="admin-field">
          <label>Titre</label>
          <input name="title" required defaultValue={event?.title ?? ""} />
        </div>
        <div className="admin-field">
          <label>Date</label>
          <input
            name="date"
            type="date"
            required
            defaultValue={event?.date ?? ""}
          />
        </div>
        <div className="admin-field">
          <label>Horaire</label>
          <input
            name="time"
            placeholder="20h00 – 22h00"
            defaultValue={event?.time ?? ""}
          />
        </div>
        <div className="admin-field" ref={wrapRef}>
          <label htmlFor={listId}>Lieu</label>
          <input
            id={listId}
            name="place"
            value={place}
            autoComplete="off"
            placeholder="Adresse, ville, lieu…"
            onChange={(e) => {
              setPlace(e.target.value);
              setOpen(true);
            }}
            onFocus={() => {
              if (suggestions.length > 0) setOpen(true);
            }}
          />
          {loading ? (
            <p className="admin-meta" style={{ marginTop: "0.35rem" }}>
              Recherche d’adresses…
            </p>
          ) : null}
          {open && suggestions.length > 0 ? (
            <ul
              role="listbox"
              className="admin-place-list"
              style={{
                listStyle: "none",
                margin: "0.35rem 0 0",
                padding: 0,
                border: "1px solid var(--line)",
                background: "var(--ink)",
                maxHeight: "14rem",
                overflow: "auto",
              }}
            >
              {suggestions.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    role="option"
                    className="admin-btn-ghost"
                    style={{
                      width: "100%",
                      justifyContent: "flex-start",
                      textAlign: "left",
                      borderRadius: 0,
                      border: "none",
                      borderBottom: "1px solid var(--line)",
                      fontWeight: 400,
                      whiteSpace: "normal",
                      height: "auto",
                      padding: "0.65rem 0.75rem",
                    }}
                    onClick={() => {
                      setPlace(item.label);
                      setSuggestions([]);
                      setOpen(false);
                    }}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
      <div className="admin-field">
        <label>Description</label>
        <textarea name="description" defaultValue={event?.description ?? ""} />
      </div>
      <button className="admin-btn" type="submit" disabled={pending}>
        {pending ? "…" : event ? "Mettre à jour" : "Ajouter"}
      </button>
    </form>
  );
}
