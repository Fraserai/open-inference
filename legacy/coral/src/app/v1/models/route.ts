/**
 * GET /v1/models
 *
 * OpenAI-compatible model listing, extended with the sovereignty metadata that
 * is the point of this product. Never returns an upstream endpoint or credential.
 */

import { PRODUCT } from "@/lib/config";
import { INTELLIGENCE_SCORE_SOURCE, listPublicModels } from "@/lib/registry";
import { newContext, requireApiKey, elapsedMs } from "@/lib/api-context";
import { operationalLog } from "@/lib/usage";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const ctx = newContext();
  const auth = requireApiKey(request, ctx);
  if (!auth.ok) return auth.response;

  const data = listPublicModels(PRODUCT.name);

  operationalLog("models_listed", {
    requestId: ctx.requestId,
    organisationId: auth.caller.organisation.id,
    count: data.length,
    latencyMs: elapsedMs(ctx),
  });

  return Response.json(
    {
      object: "list",
      data,
      intelligence_score_attribution: {
        source: INTELLIGENCE_SCORE_SOURCE.name,
        url: INTELLIGENCE_SCORE_SOURCE.url,
        note: INTELLIGENCE_SCORE_SOURCE.disclaimer,
      },
    },
    { headers: { "x-request-id": ctx.requestId, "cache-control": "no-store" } },
  );
}
