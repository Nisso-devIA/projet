import fs from "fs/promises";
import path from "path";
import type { Catalog, MouleRecord } from "@/lib/store";
import { getDataDir, readCatalog } from "@/lib/store";

function prodDataDir() {
  return process.env.PROD_DATA_DIR?.trim() || "";
}

function prodPublicDir() {
  return (
    process.env.PROD_PUBLIC_DIR?.trim() ||
    (prodDataDir()
      ? path.join(path.dirname(prodDataDir()), "public")
      : "")
  );
}

export function canPublishToProd() {
  return (
    process.env.ALLOW_PUBLISH_TO_PROD === "1" &&
    Boolean(prodDataDir()) &&
    prodDataDir() !== getDataDir()
  );
}

async function pathExists(p: string) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function copyPathIfExists(src: string, dest: string) {
  if (!(await pathExists(src))) return false;
  await fs.mkdir(path.dirname(dest), { recursive: true });
  const st = await fs.stat(src);
  if (st.isDirectory()) {
    await fs.cp(src, dest, { recursive: true, force: true });
  } else {
    await fs.copyFile(src, dest);
  }
  return true;
}

async function readProdCatalog(prodRoot: string): Promise<Catalog> {
  const file = path.join(prodRoot, "catalog.json");
  const raw = await fs.readFile(file, "utf8");
  return JSON.parse(raw) as Catalog;
}

async function writeProdCatalog(prodRoot: string, catalog: Catalog) {
  const file = path.join(prodRoot, "catalog.json");
  const tmp = `${file}.${process.pid}.tmp`;
  await fs.writeFile(tmp, `${JSON.stringify(catalog, null, 2)}\n`, "utf8");
  await fs.rename(tmp, file);
}

/** Copie un moule (meta + fichiers) de DATA_DIR test → PROD_DATA_DIR. */
export async function publishMouleToProd(mouleId: string) {
  if (!canPublishToProd()) {
    throw new Error("Publication vers la prod non autorisée sur cette instance.");
  }
  const prodRoot = prodDataDir();
  const testRoot = getDataDir();
  if (!prodRoot || !(await pathExists(path.join(prodRoot, "catalog.json")))) {
    throw new Error("PROD_DATA_DIR invalide (catalog.json introuvable).");
  }

  const testCatalog = await readCatalog();
  const moule = testCatalog.moules.find((m) => m.id === mouleId);
  if (!moule) throw new Error("Moule introuvable sur test.");

  // Backup catalogue prod
  const backupDir = path.join(
    path.dirname(prodRoot),
    "backups-publish",
    new Date().toISOString().replace(/[:.]/g, "-"),
  );
  await fs.mkdir(backupDir, { recursive: true });
  await fs.copyFile(
    path.join(prodRoot, "catalog.json"),
    path.join(backupDir, "catalog.json"),
  );

  // Fichiers data
  await copyPathIfExists(
    path.join(testRoot, "recettes", mouleId),
    path.join(prodRoot, "recettes", mouleId),
  );
  await copyPathIfExists(
    path.join(testRoot, "flip", mouleId),
    path.join(prodRoot, "flip", mouleId),
  );
  await copyPathIfExists(
    path.join(testRoot, "merged", `${mouleId}.pdf`),
    path.join(prodRoot, "merged", `${mouleId}.pdf`),
  );

  // Images uploadées (data/images/moules/<id>.*)
  const imgDir = path.join(testRoot, "images", "moules");
  try {
    const entries = await fs.readdir(imgDir);
    for (const name of entries) {
      if (path.parse(name).name !== mouleId) continue;
      await copyPathIfExists(
        path.join(imgDir, name),
        path.join(prodRoot, "images", "moules", name),
      );
    }
  } catch {
    /* pas d’images data */
  }

  // Image /brand/... dans public
  if (moule.image?.startsWith("/brand/")) {
    const pubTest =
      process.env.TEST_PUBLIC_DIR?.trim() ||
      path.join(path.dirname(testRoot), "public");
    const pubProd = prodPublicDir();
    const rel = moule.image.replace(/^\//, "");
    if (pubProd) {
      await copyPathIfExists(path.join(pubTest, rel), path.join(pubProd, rel));
    }
  }

  const prodCatalog = await readProdCatalog(prodRoot);
  const clone: MouleRecord = structuredClone(moule);
  const idx = prodCatalog.moules.findIndex((m) => m.id === mouleId);
  const replaced = idx >= 0;
  if (replaced) prodCatalog.moules[idx] = clone;
  else prodCatalog.moules.push(clone);
  await writeProdCatalog(prodRoot, prodCatalog);

  return {
    ok: true as const,
    mouleId,
    title: moule.title,
    replaced,
    recettes: moule.recettes.length,
    backupDir,
  };
}
