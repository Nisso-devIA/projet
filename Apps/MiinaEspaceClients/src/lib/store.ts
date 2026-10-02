import fs from "fs/promises";
import path from "path";

export type RecetteKind = "sucre" | "sale";

export type RecetteFile = {
  id: string;
  filename: string;
  originalName: string;
  addedAt: string;
  /** Titre affiché dans le sommaire client */
  title: string;
  /** Sucré ou salé — catégories du sommaire */
  kind: RecetteKind;
  /** Pages PNG générées pour le flipbook de cette recette */
  flipPageCount?: number;
  readyAt?: string | null;
};

export type MouleRecord = {
  id: string;
  title: string;
  image?: string;
  /** Lien FlipHTML5 de secours si aucune recette */
  fallbackHref?: string;
  recettes: RecetteFile[];
  /** @deprecated fusion abandonnée — gardé pour anciens catalogues */
  mergedAt?: string | null;
  /** @deprecated flip désormais par recette */
  flipPageCount?: number;
};

export type Catalog = {
  entretienHref: string;
  /** @deprecated bannière = toujours /brand/entretien.png */
  entretienImage?: string;
  /** Pages du feuilletage entretien (comme les recettes) */
  entretienFlipPageCount?: number;
  entretienReadyAt?: string | null;
  entretienOriginalName?: string;
  moules: MouleRecord[];
};

const DEFAULT_CATALOG: Catalog = {
  entretienHref: "https://online.fliphtml5.com/ulmmn/rqou/",
  moules: [
    {
      id: "briochettes",
      title: "Moule 12 briochettes",
      image: "/brand/moules/briochettes.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/qlir/",
      recettes: [],
    },
    {
      id: "cakes-longs",
      title: "Moule 5 cakes longs",
      image: "/brand/moules/cakes-longs.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/rgwi/",
      recettes: [],
    },
    {
      id: "carre",
      title: "Moule carré",
      image: "/brand/moules/carre.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/phkl/",
      recettes: [],
    },
    {
      id: "rond-flute",
      title: "Moule rond flûté",
      image: "/brand/moules/rond-flute.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/hzkl/",
      recettes: [],
    },
    {
      id: "oursons",
      title: "Moule oursons",
      image: "/brand/moules/oursons.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/lcug/",
      recettes: [],
    },
    {
      id: "madeleines",
      title: "Moule madeleines",
      image: "/brand/moules/madeleines.png",
      fallbackHref: "https://online.fliphtml5.com/ulmmn/hwjl/",
      recettes: [],
    },
  ],
};

export function getDataDir() {
  const custom = process.env.DATA_DIR?.trim();
  if (custom) return custom;
  return path.join(process.cwd(), "data");
}

export function catalogPath() {
  return path.join(getDataDir(), "catalog.json");
}

export function recettesDir(mouleId: string) {
  return path.join(getDataDir(), "recettes", mouleId);
}

export function mergedPdfPath(mouleId: string) {
  return path.join(getDataDir(), "merged", `${mouleId}.pdf`);
}

export function mouleImagesDir() {
  return path.join(getDataDir(), "images", "moules");
}

export function mouleImagePublicPath(mouleId: string, version?: string | number) {
  const q = version != null ? `?v=${version}` : "";
  return `/api/moules/${encodeURIComponent(mouleId)}/image${q}`;
}

export function titleFromPdfName(originalName: string) {
  const base = originalName.replace(/\.pdf$/i, "").trim();
  const cleaned = base.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  return cleaned || "Recette";
}

export function parseRecetteKind(value: unknown): RecetteKind | null {
  if (value === "sucre" || value === "sale") return value;
  return null;
}

export function recetteKindLabel(kind: RecetteKind) {
  return kind === "sale" ? "Salé" : "Sucré";
}

function normalizeRecette(raw: RecetteFile): RecetteFile {
  return {
    ...raw,
    title:
      raw.title?.trim() ||
      titleFromPdfName(raw.originalName || raw.filename || "Recette"),
    kind: parseRecetteKind(raw.kind) ?? "sucre",
    flipPageCount: raw.flipPageCount ?? 0,
    readyAt: raw.readyAt ?? null,
  };
}

function normalizeCatalog(parsed: Catalog): Catalog {
  return {
    ...parsed,
    entretienHref:
      parsed.entretienHref?.trim() || DEFAULT_CATALOG.entretienHref,
    entretienImage: parsed.entretienImage?.trim() || undefined,
    entretienFlipPageCount: parsed.entretienFlipPageCount ?? 0,
    entretienReadyAt: parsed.entretienReadyAt ?? null,
    entretienOriginalName: parsed.entretienOriginalName?.trim() || undefined,
    moules: (parsed.moules || []).map((m) => ({
      ...m,
      recettes: (m.recettes || []).map(normalizeRecette),
    })),
  };
}

async function ensureDirs() {
  const root = getDataDir();
  await fs.mkdir(path.join(root, "recettes"), { recursive: true });
  await fs.mkdir(path.join(root, "merged"), { recursive: true });
  await fs.mkdir(path.join(root, "flip"), { recursive: true });
  await fs.mkdir(mouleImagesDir(), { recursive: true });
  await fs.mkdir(path.join(root, "images", "entretien"), { recursive: true });
  await fs.mkdir(path.join(root, "entretien"), { recursive: true });
}

export async function readCatalog(): Promise<Catalog> {
  await ensureDirs();
  const file = catalogPath();
  try {
    const raw = await fs.readFile(file, "utf8");
    const parsed = JSON.parse(raw) as Catalog;
    if (!parsed.moules?.length) return structuredClone(DEFAULT_CATALOG);
    return normalizeCatalog(parsed);
  } catch {
    const seed = structuredClone(DEFAULT_CATALOG);
    await fs.writeFile(file, JSON.stringify(seed, null, 2), "utf8");
    return seed;
  }
}

export async function writeCatalog(catalog: Catalog) {
  await ensureDirs();
  await fs.writeFile(
    catalogPath(),
    JSON.stringify(normalizeCatalog(catalog), null, 2),
    "utf8",
  );
}

export async function getMoule(id: string) {
  const catalog = await readCatalog();
  return catalog.moules.find((m) => m.id === id) ?? null;
}

export async function getRecette(mouleId: string, recetteId: string) {
  const moule = await getMoule(mouleId);
  if (!moule) return null;
  const recette = moule.recettes.find((r) => r.id === recetteId) ?? null;
  if (!recette) return null;
  return { moule, recette };
}

export function slugifyId(input: string) {
  return input
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

export function mouleHasRecettes(moule: MouleRecord) {
  return moule.recettes.length > 0;
}

/** @deprecated alias */
export function mouleHasMergedPdf(moule: MouleRecord) {
  return mouleHasRecettes(moule);
}

export function recetteFlipReady(recette: RecetteFile) {
  return (recette.flipPageCount ?? 0) > 0;
}

export function mouleHasReadyRecette(moule: MouleRecord) {
  return moule.recettes.some(recetteFlipReady);
}

/** @deprecated flip prêt au niveau moule (ancien modèle fusion) */
export function mouleFlipReady(moule: MouleRecord) {
  return mouleHasReadyRecette(moule);
}

export function mouleViewerHref(moule: MouleRecord) {
  if (mouleHasRecettes(moule)) {
    return `/espace/moule/${moule.id}`;
  }
  return moule.fallbackHref || "#";
}
