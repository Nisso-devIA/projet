import Image from "next/image";
import {
  deleteInstructorAction,
  saveInstructorAction,
} from "@/app/dojo-admin/actions";
import { InstructorForm } from "@/components/admin/InstructorForm";
import { getInstructors } from "@/content/club-data";

export default async function AdminInstructorsPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const list = await getInstructors();
  return (
    <>
      <h1 className="font-display text-3xl mb-2">Instructeurs</h1>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}

      <div className="admin-card">
        <h2 className="text-xl">Ajouter</h2>
        <InstructorForm action={saveInstructorAction} />
      </div>

      {list.map((person) => (
        <div key={person.id} className="admin-card">
          {person.image ? (
            <Image
              src={person.image}
              alt={person.name}
              width={72}
              height={72}
              className="admin-thumb mb-3"
            />
          ) : null}
          <InstructorForm action={saveInstructorAction} person={person} />
          <form action={deleteInstructorAction} className="mt-2">
            <input type="hidden" name="id" value={person.id} />
            <button type="submit" className="admin-btn admin-btn-ghost">
              Supprimer
            </button>
          </form>
        </div>
      ))}
    </>
  );
}
