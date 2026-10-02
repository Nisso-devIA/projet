/**
 * Régénère les flipbooks unitaires pour toutes les recettes.
 * Usage VPS : npx --yes tsx scripts/regen-recette-flips.ts
 */
import { readCatalog } from "../src/lib/store";
import { prepareRecetteFlip } from "../src/lib/prepare-recette";

async function main() {
  const catalog = await readCatalog();
  let ok = 0;
  let fail = 0;
  for (const moule of catalog.moules) {
    for (const recette of moule.recettes) {
      process.stdout.write(`${moule.id}/${recette.id} (${recette.title})… `);
      try {
        const pages = await prepareRecetteFlip(moule.id, recette.id);
        console.log(`${pages} pages`);
        ok += 1;
      } catch (err) {
        fail += 1;
        console.log("FAIL", err instanceof Error ? err.message : err);
      }
    }
  }
  console.log(`DONE ok=${ok} fail=${fail}`);
  if (fail) process.exit(1);
}

main();
