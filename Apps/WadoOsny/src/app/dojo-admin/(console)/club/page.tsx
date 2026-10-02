import { saveClubAction } from "@/app/dojo-admin/actions";
import { ClubForm } from "@/components/admin/ClubForm";
import { getClub } from "@/content/club-data";

export default async function AdminClubPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const club = await getClub();
  return (
    <>
      <h1 className="font-display text-3xl mb-2">Club / contact</h1>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}
      <ClubForm action={saveClubAction} club={club} />
    </>
  );
}
