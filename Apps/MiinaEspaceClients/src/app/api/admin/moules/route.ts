import { NextResponse } from "next/server";
import {
  readCatalog,
  slugifyId,
  writeCatalog,
  type MouleRecord,
} from "@/lib/store";

export async function POST(request: Request) {
  let title = "";
  let fallbackHref = "";
  let image = "";
  try {
    const body = (await request.json()) as {
      title?: string;
      fallbackHref?: string;
      image?: string;
      id?: string;
    };
    title = body.title?.trim() ?? "";
    fallbackHref = body.fallbackHref?.trim() ?? "";
    image = body.image?.trim() ?? "";
    const customId = body.id?.trim();
    if (!title) {
      return NextResponse.json({ error: "Titre requis" }, { status: 400 });
    }
    const catalog = await readCatalog();
    let id = customId ? slugifyId(customId) : slugifyId(title);
    if (!id) id = `moule-${Date.now()}`;
    if (catalog.moules.some((m) => m.id === id)) {
      id = `${id}-${Date.now().toString(36)}`;
    }
    const moule: MouleRecord = {
      id,
      title,
      image: image || undefined,
      fallbackHref: fallbackHref || undefined,
      recettes: [],
      mergedAt: null,
    };
    catalog.moules.push(moule);
    await writeCatalog(catalog);
    return NextResponse.json(moule);
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }
}
