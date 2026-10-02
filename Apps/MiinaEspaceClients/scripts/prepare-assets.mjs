/**
 * Prépare les assets SANS compression JPEG (PNG uniquement).
 * - UI welcome / entretien / titre : fond retiré (transparent) → fond site #FAF2E6
 * - Bouton « Voir les recettes » + moules : fond remplacé par #FAF2E6
 */
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { loadImage, createCanvas } = require("@napi-rs/canvas");

const ROOT = process.cwd();
const OUT = path.join(ROOT, "public", "brand");
const MOULES = path.join(OUT, "moules");
const BG = [250, 242, 230]; // #FAF2E6

fs.mkdirSync(MOULES, { recursive: true });

const uiSources = {
  welcome: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.07.57 (3).jpeg"),
  entretien: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.07.57 (2).jpeg"),
  titre: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.07.57 (1).jpeg"),
  btn: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.07.57.jpeg"),
};

function knockNearWhiteToAlpha(data, hard = 245, soft = 210) {
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    if (sat > 22) continue;
    if (lum >= hard) data[i + 3] = 0;
    else if (lum >= soft)
      data[i + 3] = Math.round(((hard - lum) / (hard - soft)) * 255);
  }
}

/** Remplace blanc / crème / pêche Canva par la couleur site (bouton). */
function replaceCardBg(data) {
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;

    let t = 0;
    if (r >= 248 && g >= 248 && b >= 248) t = 1;
    else if (r > 236 && g > 236 && b > 236 && sat < 12) t = (Math.min(r, g, b) - 236) / 20;
    else if (lum > 185 && r > 200 && g > 175 && b > 140 && sat < 55) t = Math.min(1, (lum - 185) / 40);
    else if (lum > 200 && sat < 25) t = Math.min(1, (lum - 200) / 30);

    if (t <= 0) continue;
    t = Math.min(1, Math.max(0, t));
    data[i] = Math.round(r * (1 - t) + BG[0] * t);
    data[i + 1] = Math.round(g * (1 - t) + BG[1] * t);
    data[i + 2] = Math.round(b * (1 - t) + BG[2] * t);
    data[i + 3] = 255;
  }
}

/** Garde le silicone + bande rose ; tout le reste → #FAF2E6. */
function isolateMoldOnSiteBg(data) {
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;

    // Bande rose Guy Demarle
    if (r > 140 && r - g > 25 && r - b > 15 && lum < 210) continue;
    // Silicone sombre / gris
    if (lum < 105) continue;
    // Ombre douce sous le moule
    if (lum < 155 && sat < 28 && r < 170 && g < 165) continue;

    data[i] = BG[0];
    data[i + 1] = BG[1];
    data[i + 2] = BG[2];
    data[i + 3] = 255;
  }
}

function cropOpaque(canvas) {
  const ctx = canvas.getContext("2d");
  const { width: w, height: h } = canvas;
  const d = ctx.getImageData(0, 0, w, h).data;
  let minX = w,
    minY = h,
    maxX = 0,
    maxY = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (d[(y * w + x) * 4 + 3] > 24) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  const pad = 6;
  minX = Math.max(0, minX - pad);
  minY = Math.max(0, minY - pad);
  maxX = Math.min(w - 1, maxX + pad);
  maxY = Math.min(h - 1, maxY + pad);
  const cw = maxX - minX + 1;
  const ch = maxY - minY + 1;
  const out = createCanvas(cw, ch);
  out.getContext("2d").drawImage(canvas, minX, minY, cw, ch, 0, 0, cw, ch);
  return out;
}

/** Bounding box des pixels différents du fond site. */
function moldBounds(data, w, h) {
  let minX = w,
    minY = h,
    maxX = 0,
    maxY = 0;
  let found = false;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const dr = Math.abs(data[i] - BG[0]);
      const dg = Math.abs(data[i + 1] - BG[1]);
      const db = Math.abs(data[i + 2] - BG[2]);
      if (dr + dg + db > 24) {
        found = true;
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (!found) return { minX: 0, minY: 0, maxX: w - 1, maxY: h - 1 };
  return { minX, minY, maxX, maxY };
}

/** Efface débris hors boîte moule (logo / texte Canva). */
function scrubOutsideMold(data, w, h, box, margin = 18) {
  const x0 = Math.max(0, box.minX - margin);
  const y0 = Math.max(0, box.minY - margin);
  const x1 = Math.min(w - 1, box.maxX + margin);
  const y1 = Math.min(h - 1, box.maxY + margin);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (x >= x0 && x <= x1 && y >= y0 && y <= y1) continue;
      const i = (y * w + x) * 4;
      data[i] = BG[0];
      data[i + 1] = BG[1];
      data[i + 2] = BG[2];
      data[i + 3] = 255;
    }
  }
}

async function makeUiTransparent(src, dest) {
  const img = await loadImage(src);
  const c = createCanvas(img.width, img.height);
  const ctx = c.getContext("2d");
  ctx.drawImage(img, 0, 0);
  const id = ctx.getImageData(0, 0, img.width, img.height);
  knockNearWhiteToAlpha(id.data);
  ctx.putImageData(id, 0, 0);
  const cropped = cropOpaque(c);
  fs.writeFileSync(dest, cropped.toBuffer("image/png"));
  console.log("ui", path.basename(dest), cropped.width, "x", cropped.height);
}

async function makeBtnOnSiteBg(src, dest) {
  const img = await loadImage(src);
  const c = createCanvas(img.width, img.height);
  const ctx = c.getContext("2d");
  ctx.fillStyle = `rgb(${BG.join(",")})`;
  ctx.fillRect(0, 0, img.width, img.height);
  ctx.drawImage(img, 0, 0);
  const id = ctx.getImageData(0, 0, img.width, img.height);
  replaceCardBg(id.data);
  ctx.putImageData(id, 0, 0);

  const d = id.data;
  let minX = img.width,
    minY = img.height,
    maxX = 0,
    maxY = 0;
  for (let y = 0; y < img.height; y++) {
    for (let x = 0; x < img.width; x++) {
      const i = (y * img.width + x) * 4;
      const dr = Math.abs(d[i] - BG[0]);
      const dg = Math.abs(d[i + 1] - BG[1]);
      const db = Math.abs(d[i + 2] - BG[2]);
      if (dr + dg + db > 18) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  const pad = 10;
  minX = Math.max(0, minX - pad);
  minY = Math.max(0, minY - pad);
  maxX = Math.min(img.width - 1, maxX + pad);
  maxY = Math.min(img.height - 1, maxY + pad);
  const cw = maxX - minX + 1;
  const ch = maxY - minY + 1;
  const out = createCanvas(cw, ch);
  out.getContext("2d").drawImage(c, minX, minY, cw, ch, 0, 0, cw, ch);
  fs.writeFileSync(dest, out.toBuffer("image/png"));
  console.log("btn", path.basename(dest), cw, "x", ch);
}

async function extractMoulesFromPdf(skipIds = new Set()) {
  const candidates = [
    path.join(ROOT, "content", "miina-site-clients.pdf"),
    path.join(process.env.USERPROFILE || "", "Downloads", "miina site clients.pdf"),
  ];
  const pdfPath = candidates.find((p) => fs.existsSync(p));
  if (!pdfPath) {
    console.warn("PDF introuvable");
    return;
  }

  const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs");
  const data = new Uint8Array(fs.readFileSync(pdfPath));
  const doc = await pdfjs.getDocument({ data, disableWorker: true }).promise;
  const page = await doc.getPage(1);
  const scale = 3.5; // plus haute résolution, PNG lossless après
  const viewport = page.getViewport({ scale });
  const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport, canvas }).promise;

  const annots = await page.getAnnotations();
  const moldLinks = annots
    .filter((a) => a.subtype === "Link" && a.url && !String(a.url).includes("/rqou/"))
    .sort((a, b) => {
      const ay = (a.rect[1] + a.rect[3]) / 2;
      const by = (b.rect[1] + b.rect[3]) / 2;
      if (Math.abs(by - ay) > 40) return by - ay;
      return a.rect[0] - b.rect[0];
    });

  const ids = [
    "briochettes",
    "cakes-longs",
    "carre",
    "rond-flute",
    "oursons",
    "madeleines",
  ];

  for (let i = 0; i < Math.min(6, moldLinks.length); i++) {
    if (skipIds.has(ids[i])) {
      console.log("skip pdf", ids[i], "(HQ déjà prêt)");
      continue;
    }
    const rect = pdfjs.Util.normalizeRect(moldLinks[i].rect);
    const [x1, y1, x2, y2] = rect;
    const [ax, ay] = viewport.convertToViewportPoint(x1, y1);
    const [bx, by] = viewport.convertToViewportPoint(x2, y2);
    const leftBtn = Math.min(ax, bx);
    const rightBtn = Math.max(ax, bx);
    const btnTop = Math.min(ay, by);
    const btnW = rightBtn - leftBtn;
    const btnH = Math.abs(by - ay);

    // Géométrie Canva : espace vertical entre rangées ≈ 0.5× largeur bouton
    const titleH = btnH * 0.72;
    const photoH = btnW * 0.5;
    const photoBottom = Math.floor(btnTop - titleH);
    const photoTop = Math.floor(photoBottom - photoH);
    const inset = Math.floor(btnW * 0.06);
    const left = Math.floor(leftBtn + inset);
    const top = Math.max(0, photoTop);
    const w = Math.max(1, Math.floor(btnW - 2 * inset));
    const h = Math.max(1, photoBottom - top);

    const crop = createCanvas(w, h);
    const cctx = crop.getContext("2d");
    cctx.fillStyle = `rgb(${BG.join(",")})`;
    cctx.fillRect(0, 0, w, h);
    cctx.drawImage(canvas, left, top, w, h, 0, 0, w, h);

    const idata = cctx.getImageData(0, 0, w, h);
    isolateMoldOnSiteBg(idata.data);
    const box = moldBounds(idata.data, w, h);
    scrubOutsideMold(idata.data, w, h, box, 10);
    cctx.putImageData(idata, 0, 0);

    const pad = 16;
    const cx0 = Math.max(0, box.minX - pad);
    const cy0 = Math.max(0, box.minY - pad);
    const cx1 = Math.min(w - 1, box.maxX + pad);
    const cy1 = Math.min(h - 1, box.maxY + pad);
    const cw = Math.max(1, cx1 - cx0 + 1);
    const ch = Math.max(1, cy1 - cy0 + 1);
    const tight = createCanvas(cw, ch);
    const tctx = tight.getContext("2d");
    tctx.fillStyle = `rgb(${BG.join(",")})`;
    tctx.fillRect(0, 0, cw, ch);
    tctx.drawImage(crop, cx0, cy0, cw, ch, 0, 0, cw, ch);

    const side = Math.max(cw, ch, 1100);
    const out = createCanvas(side, side);
    const octx = out.getContext("2d");
    octx.fillStyle = `rgb(${BG.join(",")})`;
    octx.fillRect(0, 0, side, side);
    const fitPad = side * 0.08;
    const fit = Math.min((side - 2 * fitPad) / cw, (side - 2 * fitPad) / ch);
    const dw = Math.round(cw * fit);
    const dh = Math.round(ch * fit);
    octx.imageSmoothingEnabled = fit < 0.999;
    octx.imageSmoothingQuality = "high";
    octx.drawImage(tight, (side - dw) / 2, (side - dh) / 2, dw, dh);

    const final = octx.getImageData(0, 0, side, side);
    isolateMoldOnSiteBg(final.data);
    octx.putImageData(final, 0, 0);

    const dest = path.join(MOULES, `${ids[i]}.png`);
    fs.writeFileSync(dest, out.toBuffer("image/png"));
    console.log("moule", ids[i], `${w}x${h}`, "→", side, fs.statSync(dest).size);
  }
}

await makeUiTransparent(uiSources.welcome, path.join(OUT, "welcome.png"));
await makeUiTransparent(uiSources.entretien, path.join(OUT, "entretien.png"));
await makeUiTransparent(uiSources.titre, path.join(OUT, "titre-moules.png"));
await makeBtnOnSiteBg(uiSources.btn, path.join(OUT, "btn-voir-recettes.png"));

/** Photos HQ déposées à la racine du projet (prioritaires sur le PDF). */
function convertTiffToPng(tiffPath, pngPath) {
  if (!fs.existsSync(tiffPath)) return null;
  if (fs.existsSync(pngPath) && fs.statSync(pngPath).mtimeMs >= fs.statSync(tiffPath).mtimeMs) {
    return pngPath;
  }
  // @napi-rs/canvas plante sur ce TIFF → conversion GDI+ Windows
  const { execFileSync } = require("child_process");
  const ps = `
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile(${JSON.stringify(tiffPath)})
$img.Save(${JSON.stringify(pngPath)}, [System.Drawing.Imaging.ImageFormat]::Png)
$img.Dispose()
`;
  execFileSync(
    "powershell.exe",
    ["-NoProfile", "-Command", ps],
    { stdio: "inherit" },
  );
  return fs.existsSync(pngPath) ? pngPath : null;
}

const carrePng = convertTiffToPng(
  path.join(ROOT, "CARRE.tiff"),
  path.join(OUT, "_carre-src.png"),
);
const oursonsPng = convertTiffToPng(
  path.join(ROOT, "OURSONS.tiff"),
  path.join(OUT, "_oursons-src.png"),
);

const hqMoldSources = {
  briochettes: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.34.46 (3).jpeg"),
  "cakes-longs": path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.34.46 (1).jpeg"),
  carre: carrePng || path.join(ROOT, "CARRE.tiff"),
  "rond-flute": path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.34.46 (2).jpeg"),
  oursons: oursonsPng || path.join(ROOT, "OURSONS.tiff"),
  madeleines: path.join(ROOT, "WhatsApp Image 2026-08-30 at 21.34.46.jpeg"),
};

async function processHqMold(id, src) {
  if (!fs.existsSync(src)) {
    console.warn("HQ manquant", id, src);
    return false;
  }
  const img = await loadImage(src);
  const w = img.width;
  const h = img.height;
  const work = createCanvas(w, h);
  const wctx = work.getContext("2d");
  wctx.fillStyle = `rgb(${BG.join(",")})`;
  wctx.fillRect(0, 0, w, h);
  wctx.drawImage(img, 0, 0);
  const idata = wctx.getImageData(0, 0, w, h);
  isolateMoldOnSiteBg(idata.data);
  wctx.putImageData(idata, 0, 0);

  const box = moldBounds(idata.data, w, h);
  const pad = Math.round(Math.min(w, h) * 0.04);
  const cx0 = Math.max(0, box.minX - pad);
  const cy0 = Math.max(0, box.minY - pad);
  const cx1 = Math.min(w - 1, box.maxX + pad);
  const cy1 = Math.min(h - 1, box.maxY + pad);
  const cw = Math.max(1, cx1 - cx0 + 1);
  const ch = Math.max(1, cy1 - cy0 + 1);

  // Carré fond site — jamais d’upscale (qualité native)
  const side = Math.max(cw, ch);
  const out = createCanvas(side, side);
  const octx = out.getContext("2d");
  octx.fillStyle = `rgb(${BG.join(",")})`;
  octx.fillRect(0, 0, side, side);
  octx.drawImage(work, cx0, cy0, cw, ch, (side - cw) / 2, (side - ch) / 2, cw, ch);

  const final = octx.getImageData(0, 0, side, side);
  isolateMoldOnSiteBg(final.data);
  octx.putImageData(final, 0, 0);

  const dest = path.join(MOULES, `${id}.png`);
  fs.writeFileSync(dest, out.toBuffer("image/png"));
  console.log("hq", id, `${w}x${h}`, "→", `${side}x${side}`, fs.statSync(dest).size, path.basename(src));
  return true;
}

const done = new Set();
for (const [id, src] of Object.entries(hqMoldSources)) {
  if (await processHqMold(id, src)) done.add(id);
}

// Fallback PDF uniquement pour les moules sans photo HQ (ex. oursons)
await extractMoulesFromPdf(done);
console.log("assets ready");
