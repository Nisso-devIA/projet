import { sitePassword } from "@/lib/auth";
import { clientPublicUrl } from "@/lib/mail";
import { escapeHtml } from "@/lib/security";

function firstName(name: string) {
  const cleaned = name.trim().replace(/\s+/g, " ");
  if (!cleaned) return "";
  return cleaned.split(" ")[0] ?? "";
}

export function welcomeEmailCopy(name: string) {
  const prenom = firstName(name);
  const greeting = prenom ? `Bonjour ${prenom},` : "Bonjour,";
  const url = clientPublicUrl();
  const password = sitePassword();

  return {
    subject: "🤎 Votre accès à l’espace recettes Miina Pâtisserie",
    greeting,
    paragraphs: [
      "Tout d’abord, un grand merci de m’avoir choisie comme conseillère Guy Demarle et pour votre confiance. 🤎",
      "Pour vous remercier, je suis ravie de vous donner accès à mon espace recettes réservé à mes clients. Vous pourrez y retrouver de nombreuses recettes adaptées aux différents moules et produits Guy Demarle, ainsi que mes propres créations.",
      "Et ce n’est que le début ! 🥰 L’espace sera régulièrement enrichi avec de nouvelles recettes au fil de mes tests et de mes découvertes.",
    ],
    accessTitle: "Votre accès :",
    url,
    password,
    cta: "Ouvrir l’espace recettes",
    closing: [
      "Cet espace représente beaucoup de travail et de temps, et j’ai vraiment souhaité en faire un petit privilège réservé à mes clients Guy Demarle.",
      "Je vous demande donc de ne pas partager le lien du site, son mot de passe ou les recettes qui s’y trouvent. Cela me permet de continuer à vous proposer ce petit plus en exclusivité. 🤎",
      "J’espère que vous y trouverez plein d’idées pour profiter au maximum de vos produits !",
      "Bonne découverte et surtout, régalez-vous ! 🥰",
    ],
    signatureLines: ["Yasmina", "Miina Pâtisserie"],
  };
}

export function welcomeEmailHtml(name: string) {
  const copy = welcomeEmailCopy(name);
  const paras = (lines: string[]) =>
    lines
      .map(
        (p) =>
          `<p style="margin:0 0 16px;">${escapeHtml(p)}</p>`,
      )
      .join("\n          ");

  return `<!DOCTYPE html>
<html lang="fr">
  <body style="margin:0;padding:24px;background:#f4ece1;color:#2a1c14;font-family:Georgia,'Times New Roman',serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;margin:0 auto;background:#fbf7f1;border-radius:20px;">
      <tr>
        <td style="padding:36px 28px;font-size:16px;line-height:1.7;">
          <p style="margin:0 0 18px;font-size:22px;line-height:1.3;">${escapeHtml(copy.greeting)}</p>
          ${paras(copy.paragraphs)}
          <p style="margin:8px 0 10px;font-weight:700;">${escapeHtml(copy.accessTitle)}</p>
          <p style="margin:0 0 6px;font-family:system-ui,sans-serif;font-size:14px;">
            🔗 Site : <a href="${escapeHtml(copy.url)}" style="color:#3a2418;">${escapeHtml(copy.url)}</a>
          </p>
          <p style="margin:0 0 18px;font-family:system-ui,sans-serif;font-size:14px;">
            🔐 Mot de passe : <strong>${escapeHtml(copy.password)}</strong>
          </p>
          <p style="margin:0 0 28px;">
            <a href="${escapeHtml(copy.url)}" style="display:inline-block;padding:12px 20px;background:#3a2418;color:#fbf7f1;text-decoration:none;border-radius:999px;font-family:system-ui,sans-serif;font-size:15px;">
              ${escapeHtml(copy.cta)}
            </a>
          </p>
          ${paras(copy.closing)}
          <p style="margin:8px 0 0;font-weight:700;">${escapeHtml(copy.signatureLines[0]!)}</p>
          <p style="margin:0;font-weight:700;">${escapeHtml(copy.signatureLines[1]!)}</p>
        </td>
      </tr>
    </table>
  </body>
</html>`;
}

export function welcomeEmailText(name: string) {
  const copy = welcomeEmailCopy(name);
  return [
    copy.greeting,
    "",
    ...copy.paragraphs,
    "",
    copy.accessTitle,
    `🔗 Site : ${copy.url}`,
    `🔐 Mot de passe : ${copy.password}`,
    "",
    ...copy.closing,
    "",
    ...copy.signatureLines,
  ].join("\n");
}
