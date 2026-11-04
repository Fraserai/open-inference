/**
 * Usage metering and operational logging.
 *
 * TWO SEPARATE CHANNELS, deliberately:
 *
 *   recordUsage()  -> durable operational metadata in the usage_events table.
 *                     Feeds billing and operational visibility. Contains no
 *                     customer content, ever.
 *
 *   operationalLog() -> stdout, structured, metadata only.
 *
 * There is no code path that writes a prompt or a completion to either channel.
 * CORAL_LOG_REQUEST_CONTENT exists only so that the decision to capture content
 * would have to be made explicitly, and it is not read by anything that stores
 * content today.
 */

import { randomUUID } from "node:crypto";
import { getDb } from "@/lib/db/client";
import { usageEvents } from "@/lib/db/schema";
import type { ModelDeployment } from "@/lib/registry/deployments";
import type { UsageTotals } from "@/lib/adapters/types";

export interface UsageRecord {
  requestId: string;
  organisationId: string | null;
  apiKeyId: string | null;
  apiModelId: string | null;
  deployment: ModelDeployment | null;
  streamed: boolean;
  usage: UsageTotals;
  latencyMs: number;
  statusCode: number;
  errorCode: string | null;
}

export function recordUsage(record: UsageRecord): void {
  try {
    getDb()
      .insert(usageEvents)
      .values({
        id: randomUUID(),
        requestId: record.requestId,
        organisationId: record.organisationId,
        apiKeyId: record.apiKeyId,
        apiModelId: record.apiModelId,
        deploymentId: record.deployment?.deploymentId ?? null,
        infrastructureProvider: record.deployment?.claim?.infrastructureProvider ?? null,
        infrastructureRegion: record.deployment?.claim?.infrastructureRegion ?? null,
        inferenceCountry: record.deployment?.claim?.inferenceCountry ?? null,
        streamed: record.streamed,
        promptTokens: record.usage.prompt_tokens,
        completionTokens: record.usage.completion_tokens,
        totalTokens: record.usage.total_tokens,
        latencyMs: record.latencyMs,
        statusCode: record.statusCode,
        errorCode: record.errorCode,
        createdAt: new Date(),
      })
      .run();
  } catch (error) {
    // Metering must never take down inference. Log and carry on.
    operationalLog("usage_write_failed", {
      requestId: record.requestId,
      error: error instanceof Error ? error.name : "unknown",
    });
  }
}

/** Structured operational log line. Metadata only — never message content. */
export function operationalLog(event: string, fields: Record<string, unknown>): void {
  console.log(JSON.stringify({ ts: new Date().toISOString(), event, ...fields }));
}

/**
 * Read usage totals out of a streamed SSE response without touching content.
 *
 * OpenAI-compatible servers put a `usage` object on the final chunk when
 * `stream_options.include_usage` is set, which the adapter requests. We parse
 * only that object and discard every delta.
 */
export function createUsageCapturingStream(
  source: ReadableStream<Uint8Array>,
  onComplete: (usage: UsageTotals) => void,
): ReadableStream<Uint8Array> {
  const reader = source.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let captured: UsageTotals = {
    prompt_tokens: null,
    completion_tokens: null,
    total_tokens: null,
  };
  let finished = false;

  /** Fires exactly once, whether the stream completed, errored, or was cancelled. */
  const finish = () => {
    if (finished) return;
    finished = true;
    onComplete(captured);
  };

  const scan = (chunk: Uint8Array) => {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const payload = trimmed.slice(5).trim();
      if (payload === "" || payload === "[DONE]") continue;
      try {
        const parsed = JSON.parse(payload) as { usage?: unknown };
        if (parsed.usage && typeof parsed.usage === "object") {
          const u = parsed.usage as Record<string, unknown>;
          const num = (v: unknown) => (typeof v === "number" ? v : null);
          captured = {
            prompt_tokens: num(u.prompt_tokens),
            completion_tokens: num(u.completion_tokens),
            total_tokens: num(u.total_tokens),
          };
        }
      } catch {
        // A partial or non-JSON frame. Ignore it; we only want the usage object.
      }
    }
  };

  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) {
          finish();
          controller.close();
          return;
        }
        scan(value);
        controller.enqueue(value);
      } catch (error) {
        // Upstream died mid-stream. Record what we have rather than losing the event.
        finish();
        controller.error(error);
      }
    },
    async cancel(reason) {
      // Client disconnected. Still meter the request.
      finish();
      await reader.cancel(reason);
    },
  });
}
