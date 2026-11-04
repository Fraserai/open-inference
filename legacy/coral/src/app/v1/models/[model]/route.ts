/**
 * GET /v1/models/{model} — OpenAI-compatible single model retrieval.
 */

import { PRODUCT } from "@/lib/config";
import { getPublicModel } from "@/lib/registry";
import { newContext, requireApiKey } from "@/lib/api-context";
import { errorResponse } from "@/lib/errors";
import { unknownModelMessage } from "@/lib/validation";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ model: string }> },
) {
  const ctx = newContext();
  const auth = requireApiKey(request, ctx);
  if (!auth.ok) return auth.response;

  const { model: requested } = await params;
  const model = getPublicModel(requested, PRODUCT.name);
  if (!model) {
    return errorResponse(
      404,
      unknownModelMessage(requested),
      "not_found_error",
      "model_not_found",
      "model",
      { "x-request-id": ctx.requestId },
    );
  }

  return Response.json(model, {
    headers: { "x-request-id": ctx.requestId, "cache-control": "no-store" },
  });
}
