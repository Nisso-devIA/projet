import { NextResponse } from "next/server";
import { ADMIN_MUST_CHANGE_COOKIE } from "@/lib/auth";
import {
  clearPasswordChangeChallenge,
  confirmPasswordChangeWithCode,
  startPasswordChangeChallenge,
  validateNewPassword,
  verifyAdminPassword,
} from "@/lib/admin-auth";
import {
  isTrustedPasswordOrigin,
  rejectedPasswordOrigin,
} from "@/lib/security";

export const runtime = "nodejs";

type Body = {
  action?: "request" | "confirm" | "cancel";
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
  code?: string;
};

export async function POST(request: Request) {
  if (!isTrustedPasswordOrigin(request)) {
    return rejectedPasswordOrigin();
  }

  let body: Body = {};
  try {
    body = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  const action = body.action || "request";

  if (action === "cancel") {
    await clearPasswordChangeChallenge();
    return NextResponse.json({ ok: true });
  }

  if (action === "confirm") {
    const code = body.code?.trim() ?? "";
    if (!/^\d{6}$/.test(code)) {
      return NextResponse.json(
        { error: "Le code doit contenir 6 chiffres" },
        { status: 400 },
      );
    }
    try {
      await confirmPasswordChangeWithCode(code);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur";
      return NextResponse.json({ error: message }, { status: 400 });
    }
    const response = NextResponse.json({ ok: true });
    response.cookies.set(ADMIN_MUST_CHANGE_COOKIE, "", {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  const currentPassword = body.currentPassword?.trim() ?? "";
  const newPassword = body.newPassword?.trim() ?? "";
  const confirmPassword = body.confirmPassword?.trim() ?? "";

  const current = await verifyAdminPassword(currentPassword);
  if (!current.ok) {
    return NextResponse.json(
      { error: "Mot de passe actuel incorrect" },
      { status: 401 },
    );
  }

  if (newPassword !== confirmPassword) {
    return NextResponse.json(
      { error: "La confirmation ne correspond pas" },
      { status: 400 },
    );
  }

  const validationError = validateNewPassword(newPassword);
  if (validationError) {
    return NextResponse.json({ error: validationError }, { status: 400 });
  }

  if (newPassword === currentPassword) {
    return NextResponse.json(
      { error: "Choisissez un mot de passe différent de l’actuel" },
      { status: 400 },
    );
  }

  try {
    const { maskedTo } = await startPasswordChangeChallenge(newPassword);
    return NextResponse.json({ ok: true, codeSent: true, maskedTo });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Erreur";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
