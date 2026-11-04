/**
 * POST /v1/chat/completions
 *
 * The single inference entry point. One request, one Australian deployment.
 *
 * SOVEREIGNTY: this handler resolves exactly one deployment for the requested
 * model. If that deployment is unconfigured, non-Australian, disabled or
 * unreachable, the request FAILS with a clear error. There is no retry against
 * a different region, no fallback provider, and no offshore backend configured
 * anywhere in this codebase for it to fall back to.
 */

import { adapterFor } from "@/lib/adapters";
import { EMPTY_USAGE, type ChatCompletionRequest } from "@/lib/adapters/types";
import { PRODUCT } from "@/lib/config";
import { errorResponse } from "@/lib/errors";
import { resolveModel } from "@/lib/registry";
import type { ModelDeployment } from "@/lib/registry/deployments";
import { chatCompletionSchema, firstIssue, unknownModelMessage } from "@/lib/validation";
import { createUsageCapturingStream, operationalLog, recordUsage } from "@/lib/usage";
import { elapsedMs, newContext, requireApiKey, type RequestContext } from "@/lib/api-context";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Headers that let a customer prove, per request, where their inference ran. */
function sovereigntyHeaders(
  ctx: RequestContext,
  deployment: ModelDeployment | null,
): Record<string, string> {
  const headers: Record<string, string> = { "x-request-id": ctx.requestId };
  if (!deployment) return headers;
  headers["x-coral-deployment"] = deployment.deploymentId;
  headers["x-coral-sovereignty"] = deployment.sovereignty.status;
  if (deployment.claim?.inferenceCountry) {
    headers["x-coral-inference-country"] = deployment.claim.inferenceCountry;
  }
  if (deployment.claim?.infrastructureRegion) {
    headers["x-coral-inference-region"] = deployment.claim.infrastructureRegion;
  }
  if (deployment.adapter === "development-mock") {
    headers["x-coral-development-mock"] = "true";
  }
  return headers;
}

export async function POST(request: Request) {
  const ctx = newContext();

  const auth = requireApiKey(request, ctx);
  if (!auth.ok) {
    recordUsage({
      requestId: ctx.requestId,
      organisationId: null,
      apiKeyId: null,
      apiModelId: null,
      deployment: null,
      streamed: false,
      usage: { ...EMPTY_USAGE },
      latencyMs: elapsedMs(ctx),
      statusCode: 401,
      errorCode: auth.code,
    });
    return auth.response;
  }

  const { organisation, apiKey } = auth.caller;

  const fail = (
    status: number,
    message: string,
    type: Parameters<typeof errorResponse>[2],
    code: string,
    param: string | null,
    apiModelId: string | null,
    deployment: ModelDeployment | null,
  ) => {
    recordUsage({
      requestId: ctx.requestId,
      organisationId: organisation.id,
      apiKeyId: apiKey.id,
      apiModelId,
      deployment,
      streamed: false,
      usage: { ...EMPTY_USAGE },
      latencyMs: elapsedMs(ctx),
      statusCode: status,
      errorCode: code,
    });
    operationalLog("chat_completion_failed", {
      requestId: ctx.requestId,
      organisationId: organisation.id,
      model: apiModelId,
      status,
      code,
      latencyMs: elapsedMs(ctx),
    });
    return errorResponse(status, message, type, code, param, sovereigntyHeaders(ctx, deployment));
  };

  // ---- body ------------------------------------------------------------
  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return fail(
      400,
      "Request body must be valid JSON.",
      "invalid_request_error",
      "invalid_json",
      null,
      null,
      null,
    );
  }

  const parsed = chatCompletionSchema.safeParse(raw);
  if (!parsed.success) {
    const issue = firstIssue(parsed.error);
    const requestedModel =
      raw && typeof raw === "object" && typeof (raw as { model?: unknown }).model === "string"
        ? (raw as { model: string }).model
        : null;
    return fail(
      400,
      issue.message,
      "invalid_request_error",
      "invalid_request",
      issue.param,
      requestedModel,
      null,
    );
  }

  const body = parsed.data as ChatCompletionRequest;

  // ---- routing ---------------------------------------------------------
  const resolution = resolveModel(body.model);

  if (!resolution.ok) {
    if (resolution.reason === "unknown_model") {
      return fail(
        404,
        unknownModelMessage(body.model),
        "not_found_error",
        "model_not_found",
        "model",
        body.model,
        null,
      );
    }
    // Configured-but-unusable. Explicitly not routed offshore.
    return fail(
      503,
      `${resolution.detail} This request was not routed to any non-Australian ` +
        `infrastructure. ${PRODUCT.name} has no offshore fallback.`,
      "sovereignty_error",
      `deployment_${resolution.reason}`,
      "model",
      body.model,
      null,
    );
  }

  const { deployment } = resolution;
  const adapter = adapterFor(deployment);

  const result = await adapter.chatCompletion(body, deployment, request.signal);

  if (!result.ok) {
    return fail(
      result.status,
      result.message,
      result.status === 503 ? "sovereignty_error" : "api_error",
      result.code,
      null,
      body.model,
      deployment,
    );
  }

  // ---- streaming -------------------------------------------------------
  if (result.streaming) {
    const stream = createUsageCapturingStream(result.stream, (usage) => {
      recordUsage({
        requestId: ctx.requestId,
        organisationId: organisation.id,
        apiKeyId: apiKey.id,
        apiModelId: body.model,
        deployment,
        streamed: true,
        usage,
        latencyMs: elapsedMs(ctx),
        statusCode: 200,
        errorCode: null,
      });
      operationalLog("chat_completion", {
        requestId: ctx.requestId,
        organisationId: organisation.id,
        model: body.model,
        deployment: deployment.deploymentId,
        streamed: true,
        totalTokens: usage.total_tokens,
        latencyMs: elapsedMs(ctx),
      });
    });

    return new Response(stream, {
      status: 200,
      headers: {
        ...sovereigntyHeaders(ctx, deployment),
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive",
      },
    });
  }

  // ---- single response -------------------------------------------------
  recordUsage({
    requestId: ctx.requestId,
    organisationId: organisation.id,
    apiKeyId: apiKey.id,
    apiModelId: body.model,
    deployment,
    streamed: false,
    usage: result.usage,
    latencyMs: elapsedMs(ctx),
    statusCode: 200,
    errorCode: null,
  });
  operationalLog("chat_completion", {
    requestId: ctx.requestId,
    organisationId: organisation.id,
    model: body.model,
    deployment: deployment.deploymentId,
    streamed: false,
    totalTokens: result.usage.total_tokens,
    latencyMs: elapsedMs(ctx),
  });

  return Response.json(result.payload, {
    status: 200,
    headers: sovereigntyHeaders(ctx, deployment),
  });
}
