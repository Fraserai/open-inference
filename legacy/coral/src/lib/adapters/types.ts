/**
 * Compute provider adapter contract.
 *
 * The public API talks to adapters, never to a GPU provider directly. Swapping
 * Firmus for Sharon AI, or vLLM for another engine, is a new adapter — not a
 * change to /v1/chat/completions.
 *
 * An adapter is handed a deployment that has ALREADY passed Australian
 * sovereignty validation. Adapters do not decide where a request goes, and no
 * adapter may reach a second backend if its own is unavailable.
 */

import type { ModelDeployment } from "@/lib/registry/deployments";

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool" | "developer";
  content: unknown;
  name?: string;
  tool_call_id?: string;
}

/** The subset of the OpenAI chat request we validate. Unknown keys pass through. */
export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  max_tokens?: number;
  max_completion_tokens?: number;
  temperature?: number;
  top_p?: number;
  n?: number;
  stop?: string | string[];
  presence_penalty?: number;
  frequency_penalty?: number;
  seed?: number;
  user?: string;
  [key: string]: unknown;
}

export interface UsageTotals {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface AdapterSuccessJson {
  ok: true;
  streaming: false;
  payload: Record<string, unknown>;
  usage: UsageTotals;
}

export interface AdapterSuccessStream {
  ok: true;
  streaming: true;
  /** Server-sent events, already in OpenAI wire format. */
  stream: ReadableStream<Uint8Array>;
}

export interface AdapterFailure {
  ok: false;
  /** HTTP status to return to the customer. */
  status: number;
  code: string;
  message: string;
}

export type AdapterResult = AdapterSuccessJson | AdapterSuccessStream | AdapterFailure;

export interface AdapterHealth {
  reachable: boolean;
  detail: string;
}

export interface ComputeAdapter {
  readonly kind: string;
  /** True when this adapter is a local stand-in rather than Australian hardware. */
  readonly isDevelopmentMock: boolean;
  chatCompletion(
    request: ChatCompletionRequest,
    deployment: ModelDeployment,
    signal?: AbortSignal,
  ): Promise<AdapterResult>;
  health(deployment: ModelDeployment): Promise<AdapterHealth>;
}

export const EMPTY_USAGE: UsageTotals = {
  prompt_tokens: null,
  completion_tokens: null,
  total_tokens: null,
};

/** Pull usage out of an OpenAI-shaped response body, tolerating its absence. */
export function readUsage(payload: unknown): UsageTotals {
  if (!payload || typeof payload !== "object") return { ...EMPTY_USAGE };
  const usage = (payload as { usage?: unknown }).usage;
  if (!usage || typeof usage !== "object") return { ...EMPTY_USAGE };
  const u = usage as Record<string, unknown>;
  const num = (v: unknown): number | null => (typeof v === "number" ? v : null);
  return {
    prompt_tokens: num(u.prompt_tokens),
    completion_tokens: num(u.completion_tokens),
    total_tokens: num(u.total_tokens),
  };
}
