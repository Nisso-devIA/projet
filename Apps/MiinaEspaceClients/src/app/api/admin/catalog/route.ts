import { NextResponse } from "next/server";
import { readCatalog } from "@/lib/store";

export async function GET() {
  const catalog = await readCatalog();
  return NextResponse.json(catalog);
}
