export function mailConfigured() {
  return Boolean(process.env.RESEND_API_KEY?.trim());
}

/** Destinataire alertes / codes admin (aligné site racine). */
export function adminAlertEmail() {
  return (
    process.env.ADMIN_ALERT_EMAIL?.trim() ||
    process.env.ADMIN_NOTIFY_EMAIL?.trim() ||
    process.env.ORDER_NOTIFY_EMAIL?.trim() ||
    process.env.EMAIL_REPLY_TO?.trim() ||
    ""
  );
}

export function mailFrom() {
  return (
    process.env.EMAIL_FROM?.trim() ||
    "Miina Pâtisserie <commandes@xn--miina-ptisserie-9jb.fr>"
  );
}

export function mailReplyTo() {
  return (
    process.env.EMAIL_REPLY_TO?.trim() || "commandes@xn--miina-ptisserie-9jb.fr"
  );
}

const PRODUCTION_SITE_URL =
  "https://miinarecettesclients.xn--miina-ptisserie-9jb.fr";

function isLoopbackHost(url: string) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return (
      host === "localhost" ||
      host === "127.0.0.1" ||
      host === "0.0.0.0" ||
      host === "::1"
    );
  } catch {
    return true;
  }
}

/** URL publique pour les mails / liens clients — jamais localhost en prod. */
export function sitePublicUrl() {
  // Accès dynamique : évite l’inline Next au build (sinon lien localhost figé).
  const fromEnv = process.env["SITE_PUBLIC_URL"]?.trim().replace(/\/$/, "");
  if (fromEnv && !isLoopbackHost(fromEnv)) return fromEnv;
  return PRODUCTION_SITE_URL;
}

/** URL espace client (prod) quand l’admin tourne sur test-prod (CLIENT_PUBLIC_URL). */
export function clientPublicUrl() {
  const client = process.env.CLIENT_PUBLIC_URL?.trim().replace(/\/$/, "");
  if (client && !isLoopbackHost(client)) return client;
  return sitePublicUrl();
}

/**
 * Base URL des liens d’invitation one-time.
 * En développement, accepte SITE_PUBLIC_URL même en loopback (localhost).
 */
export function inviteAccessBaseUrl() {
  const fromEnv = process.env["SITE_PUBLIC_URL"]?.trim().replace(/\/$/, "");
  if (fromEnv) {
    if (
      process.env.NODE_ENV !== "production" ||
      !isLoopbackHost(fromEnv)
    ) {
      return fromEnv;
    }
  }
  return sitePublicUrl();
}

export function inviteAccessUrl(rawToken: string) {
  return `${inviteAccessBaseUrl()}/acces/${encodeURIComponent(rawToken)}`;
}

/** Lien page changement MDP admin (mails J-7 / J-2) — jamais localhost. */
export function adminChangePasswordUrl() {
  const fromEnv = process.env["ADMIN_CHANGE_PASSWORD_URL"]?.trim().replace(
    /\/$/,
    "",
  );
  if (fromEnv && !isLoopbackHost(fromEnv)) return fromEnv;
  return `${sitePublicUrl()}/miina-admin/change-password`;
}

export async function sendResend(payload: Record<string, unknown>) {
  const resendKey = process.env.RESEND_API_KEY?.trim();
  if (!resendKey) {
    return { ok: false as const, error: "RESEND_API_KEY manquant" };
  }
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${resendKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    console.error("[mail] Resend", res.status, detail);
    return { ok: false as const, error: "Envoi e-mail échoué" };
  }
  return { ok: true as const };
}
