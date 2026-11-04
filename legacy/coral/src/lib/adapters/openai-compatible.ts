/**
 * Adapter for any OpenAI-compatible inference server running on Australian
 * compute — vLLM, SGLang, TGI's OpenAI route, or a provider gateway that
 * speaks the same wire format.
 *
 * This is the adapter that talks to real Australian GPUs. It has exactly one
 * endpoint: the one on the deployment it was handed. If that endpoint is down,
 * it reports the failure. It has no knowledge of any other backend and cannot
 * retry anywhere else.
 */

import { upstreamTimeoutMs } from "@/lib/config";
import type { ModelDeployment } from "@/lib/registry/deployments";
import {
  readUsage,
  type AdapterHealth,
  type AdapterResult,
  type ChatCompletionRequest,
  type ComputeAdapter,
} from "./types";

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export class OpenAiCompatibleAdapter implements ComputeAdapter {
  readonly kind = "openai-compatible";
  readonly isDevelopmentMock = false;

  async chatCompletion(
    request: ChatCompletionRequest,
    deployment: ModelDeployment,
    signal?: AbortSignal,
  ): Promise<AdapterResult> {
    if (!deployment.endpoint) {
      return {
        ok: false,
        status: 503,
        code: "deployment_unavailable",
        message: "No Australian endpoint is configured for this model.",
      };
    }

    const streaming = request.stream === true;

    // Translate our public model ID to whatever the backend calls the model.
    const body: Record<string, unknown> = {
      ...request,
      model: deployment.upstreamModelId,
    };

    // Ask for usage in the final streaming chunk so we can meter streamed
    // requests without ever inspecting the content.
    if (streaming && body.stream_options === undefined) {
      body.stream_options = { include_usage: true };
    }

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (deployment.upstreamApiKey) {
      headers.Authorization = `Bearer ${deployment.upstreamApiKey}`;
    }

    const timeout = AbortSignal.timeout(upstreamTimeoutMs());
    const composite = signal ? AbortSignal.any([signal, timeout]) : timeout;

    let upstream: Response;
    try {
      upstream = await fetch(joinUrl(deployment.endpoint, "chat/completions"), {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: composite,
        cache: "no-store",
      });
    } catch (error) {
      // The Australian endpoint is unreachable. This is where a lesser design
      // would fail over to an offshore provider. We fail instead.
      const name = error instanceof Error ? error.name : "Error";
      return {
        ok: false,
        status: 503,
        code: "australian_deployment_unreachable",
        message:
          `The Australian deployment for this model could not be reached (${name}). ` +
          `This request was not sent anywhere else.`,
      };
    }

    if (!upstream.ok) {
      const detail = await upstream.text().catch(() => "");
      return {
        ok: false,
        status: upstream.status >= 500 ? 502 : upstream.status,
        code: "upstream_error",
        message:
          `The Australian inference server returned ${upstream.status}.` +
          (detail ? ` ${detail.slice(0, 500)}` : ""),
      };
    }

    if (streaming) {
      if (!upstream.body) {
        return {
          ok: false,
          status: 502,
          code: "upstream_error",
          message: "The Australian inference server returned an empty stream.",
        };
      }
      return { ok: true, streaming: true, stream: upstream.body };
    }

    let payload: Record<string, unknown>;
    try {
      payload = (await upstream.json()) as Record<string, unknown>;
    } catch {
      return {
        ok: false,
        status: 502,
        code: "upstream_error",
        message: "The Australian inference server returned a malformed response.",
      };
    }

    // Present our public model ID back to the customer, not the backend's name.
    payload.model = request.model;

    return { ok: true, streaming: false, payload, usage: readUsage(payload) };
  }

  async health(deployment: ModelDeployment): Promise<AdapterHealth> {
    if (!deployment.endpoint) {
      return { reachable: false, detail: "no endpoint configured" };
    }
    try {
      const res = await fetch(joinUrl(deployment.endpoint, "models"), {
        method: "GET",
        headers: deployment.upstreamApiKey
          ? { Authorization: `Bearer ${deployment.upstreamApiKey}` }
          : {},
        signal: AbortSignal.timeout(5000),
        cache: "no-store",
      });
      return res.ok
        ? { reachable: true, detail: "ok" }
        : { reachable: false, detail: `http ${res.status}` };
    } catch (error) {
      const name = error instanceof Error ? error.name : "Error";
      return { reachable: false, detail: `unreachable: ${name}` };
    }
  }
}
