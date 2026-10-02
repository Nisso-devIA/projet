import type { Metadata } from "next";
import { MediaGallery } from "@/components/MediaGallery";
import { PageHero } from "@/components/PageHero";
import { getGallery } from "@/content/club-data";

export const metadata: Metadata = {
  title: "Médiathèque",
  description:
    "Photos du club Wado-Osny — stages, cours, enfants et TSYR à Osny.",
};

export default async function MediathequePage() {
  const items = await getGallery();
  return (
    <>
      <PageHero
        eyebrow="Galerie"
        title="Médiathèque"
        description="Stages, cours et moments de vie au dojo — cliquez sur une photo pour l’agrandir."
      />
      <section className="mx-auto max-w-7xl px-5 py-14 md:px-8 md:py-20">
        <MediaGallery items={items} />
      </section>
    </>
  );
}
