import Image from "next/image";
import {
  addGalleryItemAction,
  deleteGalleryItemAction,
  moveGalleryItemAction,
  updateGalleryItemAction,
} from "@/app/dojo-admin/actions";
import { GalleryAddForm, GalleryEditForm } from "@/components/admin/GalleryForms";
import { getGallery } from "@/content/club-data";

export default async function AdminGalleryPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const items = await getGallery();

  return (
    <>
      <h1 className="font-display text-3xl mb-2">Médiathèque</h1>
      <p className="admin-meta mb-6">PNG, JPG ou WEBP — 5 Mo max.</p>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}

      <div className="admin-card">
        <h2 className="text-xl">Ajouter une photo</h2>
        <GalleryAddForm action={addGalleryItemAction} />
      </div>

      {items.map((item) => (
        <div key={item.id} className="admin-card flex flex-col gap-4 sm:flex-row">
          <Image
            src={item.src}
            alt={item.alt}
            width={72}
            height={72}
            className="admin-thumb"
          />
          <div className="flex-1">
            <GalleryEditForm action={updateGalleryItemAction} item={item} />
            <div className="admin-actions">
              <form action={moveGalleryItemAction}>
                <input type="hidden" name="id" value={item.id} />
                <input type="hidden" name="dir" value="up" />
                <button type="submit" className="admin-btn admin-btn-ghost">
                  ↑
                </button>
              </form>
              <form action={moveGalleryItemAction}>
                <input type="hidden" name="id" value={item.id} />
                <input type="hidden" name="dir" value="down" />
                <button type="submit" className="admin-btn admin-btn-ghost">
                  ↓
                </button>
              </form>
              <form action={deleteGalleryItemAction}>
                <input type="hidden" name="id" value={item.id} />
                <button type="submit" className="admin-btn admin-btn-ghost">
                  Supprimer
                </button>
              </form>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}
