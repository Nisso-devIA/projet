"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { Catalog, MouleRecord, RecetteKind } from "@/lib/store";
import { AdminShell } from "@/components/admin/AdminShell";

type PendingPdf = {
  key: string;
  file: File;
};

type Props = {
  initialCatalog: Catalog;
  passwordExpiry?: {
    warnWithin48h: boolean;
    hoursLeft: number | null;
    expiresAt: string | null;
    updatedAt: string | null;
  } | null;
};

export function AdminDashboard({ initialCatalog, passwordExpiry }: Props) {
  const [catalog, setCatalog] = useState(initialCatalog);
  const [selectedId, setSelectedId] = useState(catalog.moules[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [pendingPdfs, setPendingPdfs] = useState<PendingPdf[]>([]);
  const [canPublish, setCanPublish] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const selected = catalog.moules.find((m) => m.id === selectedId) ?? null;

  useEffect(() => {
    setPendingPdfs([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [selectedId]);

  useEffect(() => {
    void fetch("/api/admin/publish-status")
      .then((r) => r.json())
      .then((d: { canPublish?: boolean }) => setCanPublish(Boolean(d.canPublish)))
      .catch(() => setCanPublish(false));
  }, []);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/admin/catalog");
    if (!res.ok) throw new Error("Chargement catalogue échoué");
    const data = (await res.json()) as Catalog;
    setCatalog(data);
    if (data.moules.length && !data.moules.some((m) => m.id === selectedId)) {
      setSelectedId(data.moules[0].id);
    }
    return data;
  }, [selectedId]);

  async function addMoule(e: FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/moules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      setNewTitle("");
      const next = await refresh();
      setSelectedId((data as MouleRecord).id);
      if (!next.moules.some((m) => m.id === (data as MouleRecord).id)) {
        setSelectedId(next.moules.at(-1)?.id ?? "");
      }
      setMessage("Moule ajouté");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function saveMoule(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    const form = new FormData(e.currentTarget);
    try {
      const res = await fetch(`/api/admin/moules/${selected.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: String(form.get("title") || ""),
          image: String(form.get("image") || ""),
          fallbackHref: String(form.get("fallbackHref") || ""),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      await refresh();
      setMessage("Moule enregistré");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function deleteMoule() {
    if (!selected) return;
    if (!confirm(`Supprimer « ${selected.title} » et tous ses PDF ?`)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/moules/${selected.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Erreur");
      }
      const next = await refresh();
      setSelectedId(next.moules[0]?.id ?? "");
      setMessage("Moule supprimé");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function publishMouleToProd() {
    if (!selected) return;
    if (
      !confirm(
        `Publier « ${selected.title} » sur la PROD ?\n\nCela remplacera ce moule en production (image + recettes + flip) si l’id existe déjà.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`/api/admin/moules/${selected.id}/publish`, {
        method: "POST",
      });
      const data = (await res.json()) as {
        error?: string;
        replaced?: boolean;
        recettes?: number;
      };
      if (!res.ok) throw new Error(data.error || "Publication échouée");
      setMessage(
        data.replaced
          ? `Publié sur la prod (moule mis à jour, ${data.recettes ?? 0} recette(s)).`
          : `Publié sur la prod (nouveau moule, ${data.recettes ?? 0} recette(s)).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function uploadImage(list: FileList | null) {
    if (!selected || !list?.[0]) return;
    const file = list[0];
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`/api/admin/moules/${selected.id}/image`, {
        method: "POST",
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Upload image échoué");
      await refresh();
      setMessage("Image mise à jour");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
      if (imageInputRef.current) imageInputRef.current.value = "";
    }
  }

  async function clearImage() {
    if (!selected?.image) return;
    if (!confirm("Retirer l’image de ce moule ?")) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/moules/${selected.id}/image`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      await refresh();
      setMessage("Image retirée");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  function queueSelectedFiles(list: FileList | null) {
    if (!list?.length) return;
    const next: PendingPdf[] = [];
    const allowed =
      /\.(pdf|png|jpe?g|webp|gif|tiff?)$/i;
    for (const file of Array.from(list)) {
      const ok =
        allowed.test(file.name) ||
        file.type === "application/pdf" ||
        file.type.startsWith("image/");
      if (!ok) {
        setError(`Ignoré (PDF ou image) : ${file.name}`);
        continue;
      }
      next.push({
        key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
        file,
      });
    }
    if (next.length) {
      setPendingPdfs((prev) => [...prev, ...next]);
      setError(null);
      setMessage(null);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function removePending(key: string) {
    setPendingPdfs((prev) => prev.filter((p) => p.key !== key));
  }

  function clearPending() {
    setPendingPdfs([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function uploadPending() {
    if (!selected || pendingPdfs.length === 0) return;
    const count = pendingPdfs.length;
    setBusy(true);
    setError(null);
    setMessage(null);
    const body = new FormData();
    for (const item of pendingPdfs) body.append("file", item.file);
    try {
      const res = await fetch(`/api/admin/moules/${selected.id}`, {
        method: "POST",
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Upload échoué");
      setPendingPdfs([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refresh();
      setMessage(
        count === 1
          ? "1 recette ajoutée (flipbook prêt)"
          : `${count} recettes ajoutées (flipbooks prêts)`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function saveRecetteTitle(recetteId: string, title: string) {
    if (!selected) return;
    const trimmed = title.trim();
    if (!trimmed) {
      setError("Titre de recette requis");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/moules/${selected.id}/recettes/${recetteId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: trimmed }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      await refresh();
      setMessage("Titre de recette enregistré");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function saveRecetteKind(recetteId: string, kind: RecetteKind) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/moules/${selected.id}/recettes/${recetteId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      await refresh();
      setMessage(kind === "sale" ? "Catégorie : salé" : "Catégorie : sucré");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function deleteRecette(recetteId: string) {
    if (!selected) return;
    if (!confirm("Retirer cette recette du moule ?")) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/moules/${selected.id}/recettes/${recetteId}`,
        { method: "DELETE" },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      await refresh();
      setMessage("Recette retirée");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminShell
      title="Moules & recettes"
      active="moules"
      passwordExpiry={passwordExpiry}
    >
      {(message || error) && (
        <p
          className={`rounded-xl px-4 py-3 text-sm font-medium ${
            error ? "bg-red-100 text-danger" : "bg-emerald-100 text-emerald-900"
          }`}
        >
          {error || message}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="flex flex-col gap-3 rounded-2xl bg-[#f3e6d4]/90 p-4">
          <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
            Moules ({catalog.moules.length})
          </p>
          <ul className="flex flex-col gap-1">
            {catalog.moules.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedId(m.id);
                    setMessage(null);
                    setError(null);
                  }}
                  className={`w-full rounded-xl px-3 py-2 text-left text-sm font-semibold transition ${
                    m.id === selectedId
                      ? "bg-accent text-white"
                      : "bg-white/60 hover:bg-white"
                  }`}
                >
                  <span className="block truncate">{m.title}</span>
                  <span
                    className={`text-[0.7rem] font-medium ${
                      m.id === selectedId ? "text-white/80" : "text-ink-soft"
                    }`}
                  >
                    {m.recettes.length} recette
                    {m.recettes.length > 1 ? "s" : ""}
                    {(() => {
                      const ready = m.recettes.filter(
                        (r) => (r.flipPageCount ?? 0) > 0,
                      ).length;
                      return ready
                        ? ` · ${ready} prête${ready > 1 ? "s" : ""}`
                        : "";
                    })()}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <form onSubmit={addMoule} className="mt-2 flex flex-col gap-2 border-t border-ink/10 pt-3">
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Nouveau moule…"
              className="rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={busy || !newTitle.trim()}
              className="rounded-full bg-ink px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
            >
              Ajouter
            </button>
          </form>
        </aside>

        <section className="rounded-2xl bg-[#f3e6d4]/90 p-5 sm:p-6">
          {!selected ? (
            <p className="text-ink-soft">Aucun moule sélectionné.</p>
          ) : (
            <div className="flex flex-col gap-6">
              <form onSubmit={saveMoule} className="flex flex-col gap-3">
                <h2 className="font-display text-2xl font-semibold">{selected.title}</h2>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  Titre
                  <input
                    name="title"
                    defaultValue={selected.title}
                    key={`title-${selected.id}`}
                    className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
                    required
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  Image du moule
                  <div className="flex flex-col gap-3 rounded-xl border border-ink/15 bg-white p-3">
                    {selected.image ? (
                      <img
                        src={selected.image}
                        alt={selected.title}
                        className="mx-auto h-28 w-auto max-w-full object-contain"
                      />
                    ) : (
                      <p className="text-center text-sm text-ink-soft">
                        Aucune image
                      </p>
                    )}
                    <input
                      ref={imageInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif,image/tiff,.png,.jpg,.jpeg,.webp,.gif,.tif,.tiff"
                      disabled={busy}
                      onChange={(e) => uploadImage(e.target.files)}
                      className="text-sm font-normal file:mr-3 file:rounded-full file:border-0 file:bg-card file:px-3 file:py-1 file:text-xs file:font-bold"
                    />
                    <p className="text-xs text-ink-soft">
                      PNG, JPG, WEBP, GIF ou TIFF — max 5&nbsp;Mo. Les TIFF sont
                      convertis en PNG. Remplace l’image actuelle.
                    </p>
                    {selected.image ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={clearImage}
                        className="self-start text-xs font-semibold text-danger hover:underline disabled:opacity-50"
                      >
                        Retirer l’image
                      </button>
                    ) : null}
                  </div>
                </label>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  Chemin public (optionnel)
                  <input
                    name="image"
                    defaultValue={selected.image || ""}
                    key={`image-${selected.id}-${selected.image || ""}`}
                    placeholder="/brand/moules/… ou laisser vide après upload"
                    className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  Lien FlipHTML5 (secours si aucun PDF)
                  <input
                    name="fallbackHref"
                    defaultValue={selected.fallbackHref || ""}
                    key={`fb-${selected.id}`}
                    className="rounded-xl border border-ink/15 bg-white px-3 py-2 font-normal"
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                  >
                    Enregistrer
                  </button>
                  <button
                    type="button"
                    onClick={deleteMoule}
                    disabled={busy}
                    className="rounded-full border border-danger/40 px-4 py-2 text-sm font-semibold text-danger disabled:opacity-50"
                  >
                    Supprimer le moule
                  </button>
                  {selected.recettes.length > 0 || selected.fallbackHref ? (
                    <a
                      href={
                        selected.recettes.length > 0
                          ? `/espace/moule/${selected.id}`
                          : selected.fallbackHref!
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-full border border-ink/20 bg-white px-4 py-2 text-sm font-semibold"
                    >
                      Prévisualiser
                    </a>
                  ) : (
                    <span
                      className="rounded-full border border-ink/10 bg-white/50 px-4 py-2 text-sm font-semibold text-ink-soft"
                      title="Ajoutez une recette (ou un lien FlipHTML5) pour prévisualiser"
                    >
                      Prévisualiser
                    </span>
                  )}
                  {canPublish ? (
                    <button
                      type="button"
                      onClick={() => void publishMouleToProd()}
                      disabled={busy}
                      className="rounded-full border border-accent bg-white px-4 py-2 text-sm font-bold text-accent hover:bg-accent/10 disabled:opacity-50"
                    >
                      Publier sur la prod
                    </button>
                  ) : null}
                </div>
              </form>

              <div className="border-t border-ink/10 pt-5">
                <h3 className="mb-3 text-sm font-bold tracking-wide uppercase">
                  Recettes ({selected.recettes.length})
                </h3>
                <p className="mb-3 text-sm text-ink-soft">
                  Chaque fichier = une recette (PDF ou image : PNG, JPG, WEBP,
                  GIF, TIFF). Au clic sur Uploader, génération flipbook
                  unitaire. Le client voit d’abord un sommaire.
                </p>

                <div className="mb-4 flex flex-col gap-3">
                  <label className="flex flex-col gap-1 text-sm font-medium">
                    Ajouter des fichiers à la file
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf,.pdf,image/png,image/jpeg,image/webp,image/gif,image/tiff,.png,.jpg,.jpeg,.webp,.gif,.tif,.tiff"
                      multiple
                      disabled={busy}
                      onChange={(e) => queueSelectedFiles(e.target.files)}
                      className="rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm font-normal file:mr-3 file:rounded-full file:border-0 file:bg-card file:px-3 file:py-1 file:text-xs file:font-bold"
                    />
                  </label>

                  {pendingPdfs.length > 0 ? (
                    <div className="rounded-xl border border-dashed border-accent/40 bg-white/50 p-3">
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-bold text-ink">
                          En attente ({pendingPdfs.length})
                        </p>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={clearPending}
                          className="text-xs font-semibold text-ink-soft hover:underline disabled:opacity-50"
                        >
                          Vider la file
                        </button>
                      </div>
                      <ul className="mb-3 flex flex-col gap-1.5">
                        {pendingPdfs.map((p, i) => (
                          <li
                            key={p.key}
                            className="flex items-center justify-between gap-2 rounded-lg bg-white px-2.5 py-1.5"
                          >
                            <span className="truncate text-sm font-medium">
                              {i + 1}. {p.file.name}
                              <span className="ml-2 text-[0.7rem] font-normal text-ink-soft">
                                {(p.file.size / 1024).toFixed(0)} Ko
                              </span>
                            </span>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => removePending(p.key)}
                              className="shrink-0 text-xs font-semibold text-danger hover:underline disabled:opacity-50"
                            >
                              Retirer
                            </button>
                          </li>
                        ))}
                      </ul>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={uploadPending}
                        className="rounded-full bg-ink px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"
                      >
                        {busy
                          ? "Traitement…"
                          : `Uploader (${pendingPdfs.length})`}
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-ink-soft">
                      Aucun fichier en attente — PDF ou images (multi-sélection
                      possible).
                    </p>
                  )}
                </div>

                {selected.recettes.length === 0 ? (
                  <p className="text-sm text-ink-soft">
                    Aucune recette — le bouton client utilisera le lien FlipHTML5
                    de secours.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {selected.recettes.map((r, i) => (
                      <li
                        key={r.id}
                        className="flex flex-col gap-2 rounded-xl bg-white/70 px-3 py-3 sm:flex-row sm:items-end sm:justify-between"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="mb-1 text-[0.7rem] text-ink-soft">
                            {i + 1}. {r.originalName}
                            {(r.flipPageCount ?? 0) > 0
                              ? ` · flip ${r.flipPageCount}p`
                              : " · flip en attente"}
                          </p>
                          <label className="flex flex-col gap-1 text-sm font-medium">
                            Titre (sommaire)
                            <input
                              key={`rt-${r.id}-${r.title}`}
                              defaultValue={r.title}
                              disabled={busy}
                              className="rounded-lg border border-ink/15 bg-white px-2.5 py-1.5 font-normal"
                              onBlur={(e) => {
                                if (e.target.value.trim() !== r.title) {
                                  void saveRecetteTitle(r.id, e.target.value);
                                }
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.currentTarget.blur();
                                }
                              }}
                            />
                          </label>
                          <fieldset className="mt-2 flex flex-wrap gap-4 text-sm font-medium">
                            <legend className="sr-only">Catégorie</legend>
                            <label className="inline-flex items-center gap-2 font-normal">
                              <input
                                type="checkbox"
                                checked={(r.kind ?? "sucre") === "sucre"}
                                disabled={busy}
                                onChange={() => {
                                  if ((r.kind ?? "sucre") !== "sucre") {
                                    void saveRecetteKind(r.id, "sucre");
                                  }
                                }}
                              />
                              Sucré
                            </label>
                            <label className="inline-flex items-center gap-2 font-normal">
                              <input
                                type="checkbox"
                                checked={(r.kind ?? "sucre") === "sale"}
                                disabled={busy}
                                onChange={() => {
                                  if ((r.kind ?? "sucre") !== "sale") {
                                    void saveRecetteKind(r.id, "sale");
                                  }
                                }}
                              />
                              Salé
                            </label>
                          </fieldset>
                        </div>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => deleteRecette(r.id)}
                          className="shrink-0 text-sm font-semibold text-danger hover:underline disabled:opacity-50"
                        >
                          Retirer
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </AdminShell>
  );
}
