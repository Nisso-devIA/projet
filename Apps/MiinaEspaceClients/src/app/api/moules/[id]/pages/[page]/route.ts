import { NextResponse } from "next/server";

/** Ancienne route flip fusionnée — remplacée par /api/moules/[id]/recettes/[recetteId]/pages/[page] */
export async function GET() {
  return NextResponse.json(
    { error: "Utilisez /api/moules/{id}/recettes/{recetteId}/pages/{page}" },
    { status: 410 },
  );
}
