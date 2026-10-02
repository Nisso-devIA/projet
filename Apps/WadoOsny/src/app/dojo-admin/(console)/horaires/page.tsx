import { saveSchedulesAction } from "@/app/dojo-admin/actions";
import { SchedulesEditor } from "@/components/admin/SchedulesEditor";
import { getSchedules } from "@/content/club-data";

export default async function AdminSchedulesPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const schedules = await getSchedules();
  return (
    <>
      <h1 className="font-display text-3xl mb-2">Horaires</h1>
      <p className="admin-meta mb-6">
        Éditez les créneaux. Un créneau par ligne : Jour | Horaire | Lieu
      </p>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}
      <SchedulesEditor action={saveSchedulesAction} initial={schedules} />
    </>
  );
}
