import { NextResponse } from "next/server";
import {
  clearAllInvites,
  createInviteWithToken,
  listInvitesPublic,
  recentInviteCount,
  revokeInviteById,
} from "@/lib/invites";
import {
  mailConfigured,
  mailFrom,
  mailReplyTo,
  sendResend,
} from "@/lib/mail";
import {
  welcomeEmailCopy,
  welcomeEmailHtml,
  welcomeEmailText,
} from "@/lib/welcome-email";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const RATE_MAX = 12;

function normalizeName(raw: string) {
  return raw.replace(/\s+/g, " ").trim().slice(0, 80);
}

function normalizeEmail(raw: string) {
  return raw.trim().toLowerCase().slice(0, 120);
}

export async function GET() {
  const invites = await listInvitesPublic();
  return NextResponse.json({ configured: mailConfigured(), invites });
}

export async function DELETE(request: Request) {
  let body: { id?: string; clearAll?: boolean } = {};
  try {
    body = (await request.json()) as { id?: string; clearAll?: boolean };
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  if (body.clearAll) {
    await clearAllInvites();
    return NextResponse.json({ ok: true, cleared: true });
  }

  const id = body.id?.trim() ?? "";
  if (!id) {
    return NextResponse.json({ error: "id manquant" }, { status: 400 });
  }

  const removed = await revokeInviteById(id);
  if (!removed) {
    return NextResponse.json({ error: "Entrée introuvable" }, { status: 404 });
  }
  return NextResponse.json({ ok: true });
}

export async function POST(request: Request) {
  if (!mailConfigured()) {
    return NextResponse.json(
      {
        error:
          "Envoi non configuré : ajoutez RESEND_API_KEY (même clé que le site recettes).",
      },
      { status: 503 },
    );
  }

  let name = "";
  let email = "";
  try {
    const body = (await request.json()) as { name?: string; email?: string };
    name = normalizeName(body.name ?? "");
    email = normalizeEmail(body.email ?? "");
  } catch {
    return NextResponse.json({ error: "Requête invalide" }, { status: 400 });
  }

  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ error: "E-mail invalide" }, { status: 400 });
  }

  const recent = await recentInviteCount(RATE_WINDOW_MS);
  if (recent >= RATE_MAX) {
    return NextResponse.json(
      {
        error:
          "Trop d’envois en peu de temps. Réessayez dans quelques minutes.",
      },
      { status: 429 },
    );
  }

  // Contenu mail = iso prod (lien site + mot de passe, pas de lien unique)
  const copy = welcomeEmailCopy(name);
  const sent = await sendResend({
    from: mailFrom(),
    reply_to: mailReplyTo(),
    to: [email],
    subject: copy.subject,
    html: welcomeEmailHtml(name),
    text: welcomeEmailText(name),
  });

  if (!sent.ok) {
    return NextResponse.json({ error: sent.error }, { status: 502 });
  }

  const { record } = await createInviteWithToken(name, email);
  return NextResponse.json({ ok: true, invite: record });
}
