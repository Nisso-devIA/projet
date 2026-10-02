"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  pageCount: number;
  title: string;
  /** Base API des pages, ex. /api/entretien/pages ou chemin moule/recette */
  pagesBaseUrl?: string;
  mouleId?: string;
  recetteId?: string;
};

const ZOOM_MIN = 1;
const ZOOM_MAX = 2.75;
const ZOOM_STEP = 0.25;

type FlipApi = {
  destroy: () => void;
  flipNext: (corner?: string) => void;
  flipPrev: (corner?: string) => void;
  getCurrentPageIndex: () => number;
  on: (event: string, cb: (e: { data: number }) => void) => void;
  update: () => void;
};

function pageUrl(
  page: number,
  opts: { pagesBaseUrl?: string; mouleId?: string; recetteId?: string },
) {
  if (opts.pagesBaseUrl) {
    return `${opts.pagesBaseUrl.replace(/\/$/, "")}/${page}`;
  }
  return `/api/moules/${encodeURIComponent(opts.mouleId!)}/recettes/${encodeURIComponent(opts.recetteId!)}/pages/${page}`;
}

function clampZoom(value: number) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(value * 100) / 100));
}

/** ChromeOS only — correctif flou GPU (filter + transform). */
function isChromebook() {
  if (typeof navigator === "undefined") return false;
  return /\bCrOS\b/.test(navigator.userAgent);
}

function fitPageSize(
  naturalW: number,
  naturalH: number,
  shortBook: boolean,
  landscape: boolean,
) {
  const maxBookW = Math.min(
    landscape ? 1100 : shortBook ? 440 : 560,
    Math.max(280, window.innerWidth - (landscape ? 48 : 40)),
  );
  const maxBookH = Math.min(window.innerHeight * (landscape ? 0.78 : 0.72), 920);
  const pageMaxW = landscape ? maxBookW / 2 : maxBookW;
  const scale = Math.min(pageMaxW / naturalW, maxBookH / naturalH, 1);
  return {
    width: Math.max(landscape ? 220 : 240, Math.round(naturalW * scale)),
    height: Math.max(300, Math.round(naturalH * scale)),
  };
}

export function FlipPdfReader({
  mouleId,
  recetteId,
  pageCount,
  title,
  pagesBaseUrl,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const flipRef = useRef<FlipApi | null>(null);
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const [page, setPage] = useState(1);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [chromebook, setChromebook] = useState(false);

  useEffect(() => {
    setChromebook(isChromebook());
  }, []);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  useEffect(() => {
    panRef.current = pan;
  }, [pan]);

  function applyZoom(next: number) {
    const z = clampZoom(next);
    setZoom(z);
    if (z <= ZOOM_MIN) setPan({ x: 0, y: 0 });
  }

  function turn(delta: number) {
    const flip = flipRef.current;
    if (!flip) return;
    if (delta > 0) flip.flipNext();
    else flip.flipPrev();
  }

  useEffect(() => {
    const blockContext = (event: Event) => event.preventDefault();
    const blockKeys = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        flipRef.current?.flipNext();
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        flipRef.current?.flipPrev();
      } else if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        applyZoom(zoomRef.current + ZOOM_STEP);
      } else if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        applyZoom(zoomRef.current - ZOOM_STEP);
      } else if (event.key === "0") {
        event.preventDefault();
        applyZoom(1);
      }
    };
    document.addEventListener("contextmenu", blockContext);
    document.addEventListener("keydown", blockKeys);
    return () => {
      document.removeEventListener("contextmenu", blockContext);
      document.removeEventListener("keydown", blockKeys);
    };
  }, []);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || !ready) return;

    let panStartX = 0;
    let panStartY = 0;
    let pinchStartDist = 0;
    let pinchStartZoom = 1;
    let touchStartX = 0;
    let touchStartY = 0;

    function dist(a: Touch, b: Touch) {
      return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    }

    function onTouchStart(event: TouchEvent) {
      if (event.touches.length === 2) {
        event.preventDefault();
        pinchStartDist = dist(event.touches[0], event.touches[1]);
        pinchStartZoom = zoomRef.current;
      } else if (event.touches.length === 1 && zoomRef.current > ZOOM_MIN + 0.01) {
        touchStartX = event.touches[0].clientX;
        touchStartY = event.touches[0].clientY;
        panStartX = panRef.current.x;
        panStartY = panRef.current.y;
      }
    }

    function onTouchMove(event: TouchEvent) {
      if (event.touches.length === 2 && pinchStartDist > 0) {
        event.preventDefault();
        applyZoom(
          pinchStartZoom *
            (dist(event.touches[0], event.touches[1]) / pinchStartDist),
        );
        return;
      }
      if (event.touches.length !== 1 || zoomRef.current <= ZOOM_MIN + 0.01) {
        return;
      }
      event.preventDefault();
      const dx = event.touches[0].clientX - touchStartX;
      const dy = event.touches[0].clientY - touchStartY;
      setPan({ x: panStartX + dx, y: panStartY + dy });
    }

    function onTouchEnd(event: TouchEvent) {
      if (event.touches.length === 0) pinchStartDist = 0;
    }

    stage.addEventListener("touchstart", onTouchStart, { passive: false });
    stage.addEventListener("touchmove", onTouchMove, { passive: false });
    stage.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      stage.removeEventListener("touchstart", onTouchStart);
      stage.removeEventListener("touchmove", onTouchMove);
      stage.removeEventListener("touchend", onTouchEnd);
    };
  }, [ready]);

  useEffect(() => {
    if (pageCount < 1) {
      setError("Aucune page.");
      return;
    }

    let cancelled = false;
    let resizeTimer = 0;
    const host = hostRef.current;
    if (!host) return;

    async function boot() {
      try {
        const { PageFlip } = await import("page-flip");
        if (cancelled || !host) return;

        const probe = new Image();
        probe.decoding = "async";
        await new Promise<void>((resolve, reject) => {
          probe.onload = () => resolve();
          probe.onerror = () => reject(new Error("load"));
          probe.src = pageUrl(1, { pagesBaseUrl, mouleId, recetteId });
        });
        if (cancelled || !host) return;

        const shortBook = pageCount <= 3;
        const landscape =
          !shortBook && window.innerWidth >= 900 && pageCount >= 4;
        const showCover = pageCount >= 4;
        const { width, height } = fitPageSize(
          probe.naturalWidth || 1000,
          probe.naturalHeight || 1414,
          shortBook,
          landscape,
        );

        host.innerHTML = "";
        host.classList.toggle("is-short-flip", shortBook);
        host.classList.toggle("is-landscape-flip", landscape);

        const book = document.createElement("div");
        book.className = "flip-book-inner";
        const pageNodes: HTMLElement[] = [];
        for (let i = 1; i <= pageCount; i++) {
          const pageEl = document.createElement("div");
          pageEl.className = "flip-html-page";
          const hard =
            showCover && (i === 1 || i === pageCount) ? "hard" : "soft";
          pageEl.setAttribute("data-density", hard);
          const img = document.createElement("img");
          img.src = pageUrl(i, { pagesBaseUrl, mouleId, recetteId });
          img.alt = `${title} — page ${i}`;
          img.draggable = false;
          img.decoding = "async";
          pageEl.appendChild(img);
          book.appendChild(pageEl);
          pageNodes.push(pageEl);
        }
        host.appendChild(book);

        const pageFlip = new PageFlip(book, {
          width,
          height,
          size: "fixed",
          minWidth: width,
          maxWidth: width,
          minHeight: height,
          maxHeight: height,
          showCover,
          drawShadow: true,
          maxShadowOpacity: 0.9,
          mobileScrollSupport: true,
          useMouseEvents: true,
          flippingTime: shortBook ? 800 : 1100,
          usePortrait: !landscape,
          startPage: 0,
          autoSize: true,
          showPageCorners: true,
          disableFlipByClick: false,
          swipeDistance: 25,
          clickEventForward: true,
        } as ConstructorParameters<typeof PageFlip>[1]);

        pageFlip.loadFromHTML(pageNodes);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        flipRef.current = pageFlip as any;

        pageFlip.on("flip", (e) => {
          setPage(Number(e.data) + 1);
        });
        pageFlip.on("init", (e) => {
          const data = e.data as { page?: number };
          if (typeof data?.page === "number") setPage(data.page + 1);
        });

        if (!cancelled) {
          setReady(true);
          setError("");
        }
      } catch {
        if (!cancelled) setError("Impossible de charger le feuilletage.");
      }
    }

    const onResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        try {
          flipRef.current?.update();
        } catch {
          /* ignore */
        }
      }, 180);
    };
    window.addEventListener("resize", onResize);
    void boot();

    return () => {
      cancelled = true;
      window.removeEventListener("resize", onResize);
      window.clearTimeout(resizeTimer);
      try {
        flipRef.current?.destroy();
      } catch {
        /* ignore */
      }
      flipRef.current = null;
      if (host) host.innerHTML = "";
    };
  }, [mouleId, recetteId, pagesBaseUrl, pageCount, title]);

  const zoomLabel = `${Math.round(zoom * 100)} %`;
  const chromebookIdle = chromebook && zoom <= ZOOM_MIN;

  return (
    <div
      className={`flip-reader${chromebook ? " is-chromebook" : ""}`}
      onContextMenu={(e) => e.preventDefault()}
    >
      <div
        ref={stageRef}
        className={`flip-reader-stage${zoom > 1 ? " is-zoomed" : ""}`}
        aria-label={title}
      >
        {!ready && !error ? (
          <p className="flip-reader-status">Préparation du feuilletage…</p>
        ) : null}
        {error ? <p className="flip-reader-status text-red-300">{error}</p> : null}
        <div
          className="flip-zoom-layer"
          style={{
            transform: chromebookIdle
              ? "none"
              : `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            visibility: ready ? "visible" : "hidden",
          }}
        >
          <div ref={hostRef} className="flip-book-host" />
        </div>
      </div>

      <div className="flip-reader-toolbar" role="toolbar" aria-label="Zoom">
        <button
          type="button"
          className="flip-btn"
          onClick={() => applyZoom(zoom - ZOOM_STEP)}
          disabled={!ready || zoom <= ZOOM_MIN}
          aria-label="Dézoomer"
        >
          −
        </button>
        <button
          type="button"
          className="flip-btn flip-zoom-reset"
          onClick={() => applyZoom(1)}
          disabled={!ready || zoom === ZOOM_MIN}
        >
          {zoomLabel}
        </button>
        <button
          type="button"
          className="flip-btn"
          onClick={() => applyZoom(zoom + ZOOM_STEP)}
          disabled={!ready || zoom >= ZOOM_MAX}
          aria-label="Zoomer"
        >
          +
        </button>
      </div>

      <div className="flip-reader-controls">
        <button
          type="button"
          className="flip-btn"
          onClick={() => turn(-1)}
          disabled={!ready || page <= 1}
        >
          ← Page précédente
        </button>
        <p className="flip-reader-page">
          Page {page} / {pageCount}
        </p>
        <button
          type="button"
          className="flip-btn"
          onClick={() => turn(1)}
          disabled={!ready || page >= pageCount}
        >
          Page suivante →
        </button>
      </div>
      <p className="flip-reader-note">
        Feuilletez · pincez pour zoomer
      </p>
    </div>
  );
}
