import { savePricingAction } from "@/app/dojo-admin/actions";
import { PricingEditor } from "@/components/admin/PricingEditor";
import { getPricing } from "@/content/club-data";

export default async function AdminPricingPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string }>;
}) {
  const { ok } = await searchParams;
  const pricing = await getPricing();
  return (
    <>
      <h1 className="font-display text-3xl mb-2">Tarifs</h1>
      {ok ? <p className="admin-ok">Enregistré.</p> : null}
      <PricingEditor action={savePricingAction} initial={pricing} />
    </>
  );
}
