import {
  deleteEventAction,
  saveEventAction,
} from "@/app/dojo-admin/actions";
import { formatEventDate, getEvents, splitEvents } from "@/content/club-data";
import { EventForm } from "@/components/admin/EventForm";

export default async function AdminEventsPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const events = await getEvents();
  const { upcoming, past } = splitEvents(events);

  return (
    <>
      <h1 className="font-display text-3xl mb-2">Événements</h1>
      <p className="admin-meta mb-6">
        Les dates futures apparaissent dans « à venir », les autres dans «
        passés ». Le lieu propose des adresses en France pendant la saisie.
      </p>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}

      <div className="admin-card">
        <h2 className="text-xl">Nouvel événement</h2>
        <EventForm action={saveEventAction} />
      </div>

      <h2 className="font-display text-2xl mt-10 mb-4">À venir</h2>
      {upcoming.length === 0 ? (
        <p className="admin-meta mb-6">Aucun événement à venir.</p>
      ) : (
        upcoming.map((event) => (
          <div key={event.id} className="admin-card">
            <h3 className="text-lg">
              {event.title}{" "}
              <span className="admin-meta">— {formatEventDate(event.date)}</span>
            </h3>
            <EventForm action={saveEventAction} event={event} />
            <form action={deleteEventAction} className="mt-2">
              <input type="hidden" name="id" value={event.id} />
              <button type="submit" className="admin-btn admin-btn-ghost">
                Supprimer
              </button>
            </form>
          </div>
        ))
      )}

      <h2 className="font-display text-2xl mt-10 mb-4">Passés</h2>
      {past.map((event) => (
        <div key={event.id} className="admin-card">
          <h3 className="text-lg">
            {event.title}{" "}
            <span className="admin-meta">— {formatEventDate(event.date)}</span>
          </h3>
          <EventForm action={saveEventAction} event={event} />
          <form action={deleteEventAction} className="mt-2">
            <input type="hidden" name="id" value={event.id} />
            <button type="submit" className="admin-btn admin-btn-ghost">
              Supprimer
            </button>
          </form>
        </div>
      ))}
    </>
  );
}
