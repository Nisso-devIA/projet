"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import type { GalleryItem } from "@/content/defaults";

const filters = ["Tous", "Stages", "Cours", "Enfants", "TSYR"] as const;

export function MediaGallery({ items: gallery }: { items: GalleryItem[] }) {
  const [filter, setFilter] = useState<(typeof filters)[number]>("Tous");
  const [active, setActive] = useState<number | null>(null);

  const items =
    filter === "Tous"
      ? gallery
      : gallery.filter((item) => item.category === filter);

  const openIndex = active;

  const close = useCallback(() => setActive(null), []);

  const prev = useCallback(() => {
    setActive((i) => {
      if (i === null || items.length === 0) return i;
      return (i - 1 + items.length) % items.length;
    });
  }, [items.length]);

  const next = useCallback(() => {
    setActive((i) => {
      if (i === null || items.length === 0) return i;
      return (i + 1) % items.length;
    });
  }, [items.length]);

  useEffect(() => {
    if (openIndex === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [openIndex, close, prev, next]);

  return (
    <>
      <div className="flex flex-wrap justify-center gap-2">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => {
              setFilter(f);
              setActive(null);
            }}
            className={`rounded-sm px-4 py-2 text-sm transition ${
              filter === f
                ? "bg-crimson text-paper"
                : "border border-line text-paper-muted hover:border-paper/40 hover:text-paper"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="mt-10 columns-1 gap-4 sm:columns-2 lg:columns-3">
        {items.map((item, index) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActive(index)}
            className="group mb-4 block w-full break-inside-avoid overflow-hidden border border-line bg-ink-lift text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-crimson-bright"
          >
            <span className="relative block aspect-[4/3] overflow-hidden">
              <Image
                src={item.src}
                alt={item.alt}
                fill
                className="object-cover transition duration-500 group-hover:scale-105"
                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              />
              <span className="absolute inset-0 bg-ink/0 transition group-hover:bg-ink/35" />
              <span className="absolute bottom-3 left-3 rounded-sm bg-ink/75 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-gold opacity-0 transition group-hover:opacity-100">
                {item.category}
              </span>
            </span>
          </button>
        ))}
      </div>

      {openIndex !== null && items[openIndex] ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={items[openIndex].alt}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/92 p-4 backdrop-blur-sm"
          onClick={close}
        >
          <button
            type="button"
            aria-label="Fermer"
            className="absolute right-4 top-4 z-10 flex h-11 w-11 items-center justify-center rounded-sm border border-line text-paper hover:bg-ink-lift"
            onClick={close}
          >
            ✕
          </button>
          <button
            type="button"
            aria-label="Photo précédente"
            className="absolute left-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-sm border border-line text-paper hover:bg-ink-lift md:left-6"
            onClick={(e) => {
              e.stopPropagation();
              prev();
            }}
          >
            ←
          </button>
          <button
            type="button"
            aria-label="Photo suivante"
            className="absolute right-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-sm border border-line text-paper hover:bg-ink-lift md:right-6"
            onClick={(e) => {
              e.stopPropagation();
              next();
            }}
          >
            →
          </button>

          <div
            className="relative max-h-[85vh] w-full max-w-5xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative aspect-[16/10] w-full overflow-hidden bg-ink-soft">
              <Image
                src={items[openIndex].src}
                alt={items[openIndex].alt}
                fill
                className="object-contain"
                sizes="100vw"
                priority
              />
            </div>
            <p className="mt-4 text-center text-sm text-paper-muted">
              {items[openIndex].alt}
              <span className="mx-2 text-line">·</span>
              {openIndex + 1} / {items.length}
            </p>
          </div>
        </div>
      ) : null}
    </>
  );
}
