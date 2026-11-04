/**
 * DEVELOPMENT MOCK ADAPTER — NOT AUSTRALIAN INFRASTRUCTURE.
 *
 * Lets the API, auth, registry, routing and usage metering run end to end with
 * no GPU attached. Everything it returns is clearly labelled as a mock:
 *
 *   - the response content says so
 *   - the response carries `x_coral_development_mock: true`
 *   - the deployment's sovereignty status is `development_mock`, never `verified`
 *
 * It is refused in production unless CORAL_ALLOW_DEVELOPMENT_MOCKS is explicitly
 * turned on, because a mock quietly answering customer traffic would be exactly
 * the false sovereignty claim this product exists to avoid.
 */

import type { ModelDeployment } from "@/lib/registry/deployments";
import type {
  AdapterHealth,
  AdapterResult,
  ChatCompletionRequest,
  ComputeAdapter,
} from "./types";

export const MOCK_NOTICE =
  "[DEVELOPMENT MOCK] This response was generated locally by a development stub. " +
  "No Australian GPU served it and no model weights were used.";

/** Crude word-based estimate. Enough to exercise metering; not a real tokeniser. */
function estimateTokens(text: string): number {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : Math.ceil(trimmed.split(/\s+/).length * 1.3);
}

function flattenContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) =>
        part && typeof part === "object" && typeof (part as { text?: unknown }).text === "string"
          ? (part as { text: string }).text
          : "",
      )
      .join(" ");
  }
  return "";
}

export class DevelopmentMockAdapter implements ComputeAdapter {
  readonly kind = "development-mock";
  readonly isDevelopmentMock = true;

  async chatCompletion(
    request: ChatCompletionRequest,
    deployment: ModelDeployment,
  ): Promise<AdapterResult> {
    const promptTokens = request.messages.reduce(
      (sum, m) => sum + estimateTokens(flattenContent(m.content)),
      0,
    );
    const content = `${MOCK_NOTICE} Model requested: ${request.model}. Deployment: ${deployment.deploymentId}.`;
    const completionTokens = estimateTokens(content);
    const id = `chatcmpl-mock-${crypto.randomUUID()}`;
    const created = Math.floor(Date.now() / 1000);

    if (request.stream === true) {
      const encoder = new TextEncoder();
      const words = content.split(" ");
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          const send = (obj: unknown) =>
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));

          send({
            id,
            object: "chat.completion.chunk",
            created,
            model: request.model,
            x_coral_development_mock: true,
            choices: [{ index: 0, delta: { role: "assistant" }, finish_reason: null }],
          });
          for (const word of words) {
            send({
              id,
              object: "chat.completion.chunk",
              created,
              model: request.model,
              x_coral_development_mock: true,
              choices: [{ index: 0, delta: { content: `${word} ` }, finish_reason: null }],
            });
          }
          send({
            id,
            object: "chat.completion.chunk",
            created,
            model: request.model,
            x_coral_development_mock: true,
            choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
            usage: {
              prompt_tokens: promptTokens,
              completion_tokens: completionTokens,
              total_tokens: promptTokens + completionTokens,
            },
          });
          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          controller.close();
        },
      });
      return { ok: true, streaming: true, stream };
    }

    return {
      ok: true,
      streaming: false,
      payload: {
        id,
        object: "chat.completion",
        created,
        model: request.model,
        x_coral_development_mock: true,
        choices: [
          {
            index: 0,
            message: { role: "assistant", content },
            finish_reason: "stop",
          },
        ],
        usage: {
          prompt_tokens: promptTokens,
          completion_tokens: completionTokens,
          total_tokens: promptTokens + completionTokens,
        },
      },
      usage: {
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens,
        total_tokens: promptTokens + completionTokens,
      },
    };
  }

  async health(): Promise<AdapterHealth> {
    return { reachable: true, detail: "development mock — no Australian GPU attached" };
  }
}
