import type { Metadata } from "next";
import { PageHero } from "@/components/PageHero";
import { getClub } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Politique de confidentialité",
};

export default async function ConfidentialitePage() {
  const club = await getClub();
  return (
    <>
      <PageHero eyebrow="RGPD" title="Politique de confidentialité" />
      <section className="mx-auto max-w-3xl space-y-8 px-5 py-16 text-paper-muted leading-relaxed md:px-8">
        <p className="text-sm">En vigueur au 15/07/2024</p>
        <p>
          Cette politique s&apos;applique au site {club.name}. Elle décrit la
          manière dont sont collectées et traitées les données personnelles
          (nom, prénom, email, etc.), les droits des utilisateurs, et le
          responsable du traitement.
        </p>
        <p>
          Responsable : {club.association} — {club.siege} —{" "}
          <a href={`mailto:${club.email}`} className="text-gold">
            {club.email}
          </a>
        </p>
        <p>
          Le formulaire de contact ouvre votre client mail (mailto) : aucune
          donnée n&apos;est stockée sur un serveur distant pour cet envoi.
        </p>
        <p>
          Vous pouvez exercer vos droits d&apos;accès, rectification, effacement
          et opposition en écrivant à {club.email}.
        </p>
      </section>
    </>
  );
}
