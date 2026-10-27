import { Storefront } from "@/components/storefront";

export default async function CatalogPage({
  params,
}: {
  params: Promise<{ tenantSlug: string }>;
}) {
  const { tenantSlug } = await params;
  return <Storefront tenantSlug={tenantSlug} />;
}
