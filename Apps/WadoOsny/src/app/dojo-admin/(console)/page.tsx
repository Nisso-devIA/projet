import Link from "next/link";
import { adminPath } from "@/lib/admin-paths";
import {
  getEvents,
  getGallery,
  getInstructors,
  splitEvents,
} from "@/content/club-data";

export default async function AdminHomePage() {
  const [events, gallery, instructors] = await Promise.all([
    getEvents(),
    getGallery(),
    getInstructors(),
  ]);
  const { upcoming } = splitEvents(events);

  const cards = [
    {
      href: "/evenements",
      title: "Événements",
      meta: `${upcoming.length} à venir · ${events.length} au total`,
    },
    {
      href: "/mediatheque",
      title: "Médiathèque",
      meta: `${gallery.length} photos`,
    },
    { href: "/horaires", title: "Horaires", meta: "Enfants & adultes" },
    { href: "/tarifs", title: "Tarifs", meta: "Cotisations" },
    {
      href: "/instructeurs",
      title: "Instructeurs",
      meta: `${instructors.length} profils`,
    },
    { href: "/club", title: "Club / contact", meta: "Email, lieux, RNA" },
  ];

  return (
    <>
      <h1 className="font-display text-3xl mb-2">Espace club</h1>
      <p className="admin-meta mb-8">
        Gérez le contenu public de wado-osny.fr
      </p>
      <div className="admin-grid-2">
        {cards.map((card) => (
          <Link
            key={card.href}
            href={adminPath(card.href)}
            className="admin-card block no-underline text-inherit"
          >
            <h2 className="text-xl">{card.title}</h2>
            <p className="admin-meta">{card.meta}</p>
          </Link>
        ))}
      </div>
    </>
  );
}
