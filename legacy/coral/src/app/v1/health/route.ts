/**
 * GET /v1/health — unauthenticated liveness and sovereignty posture.
 *
 * Reports counts, never endpoints. A model appears as sovereign here only if a
 * verified Australian deployment is configured for it.
 */

import { CATALOGUE } from "@/lib/registry/catalogue";
import { getDeployments } from "@/lib/registry/deployments";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const deployments = getDeployments();
  const statuses = CATALOGUE.map((m) => deployments.get(m.apiModelId));

  return Response.json(
    {
      status: "ok",
      catalogue_models: CATALOGUE.length,
      routable_models: statuses.filter(
        (d) => d?.status === "active" || d?.status === "development_mock",
      ).length,
      sovereignty_verified_models: statuses.filter((d) => d?.sovereignty.isSovereign).length,
      development_mocks: statuses.filter((d) => d?.status === "development_mock").length,
      offshore_fallback: "none",
    },
    { headers: { "cache-control": "no-store" } },
  );
}
