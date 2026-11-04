import { describe, expect, it } from "vitest";
import { createUsageCapturingStream } from "@/lib/usage";
import type { UsageTotals } from "@/lib/adapters/types";

function sseStream(frames: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const f of frames) controller.enqueue(encoder.encode(f));
      controller.close();
    },
  });
}

async function drain(stream: ReadableStream<Uint8Array>): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let out = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    out += decoder.decode(value, { stream: true });
  }
  return out;
}

describe("streamed usage capture", () => {
  it("extracts usage from the final chunk and passes the stream through unchanged", async () => {
    const frames = [
      `data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n`,
      `data: {"choices":[{"delta":{"content":"lo"}}]}\n\n`,
      `data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":9,"completion_tokens":2,"total_tokens":11}}\n\n`,
      `data: [DONE]\n\n`,
    ];

    let captured: UsageTotals | null = null;
    const wrapped = createUsageCapturingStream(sseStream(frames), (u) => {
      captured = u;
    });

    const output = await drain(wrapped);
    expect(output).toBe(frames.join(""));
    expect(captured).toEqual({ prompt_tokens: 9, completion_tokens: 2, total_tokens: 11 });
  });

  it("reports nulls rather than guessing when the server sends no usage", async () => {
    let captured: UsageTotals | null = null;
    const wrapped = createUsageCapturingStream(
      sseStream([`data: {"choices":[{"delta":{"content":"x"}}]}\n\n`, `data: [DONE]\n\n`]),
      (u) => {
        captured = u;
      },
    );
    await drain(wrapped);
    expect(captured).toEqual({
      prompt_tokens: null,
      completion_tokens: null,
      total_tokens: null,
    });
  });

  it("survives frames split across chunk boundaries", async () => {
    let captured: UsageTotals | null = null;
    const wrapped = createUsageCapturingStream(
      sseStream([
        `data: {"choices":[],"usa`,
        `ge":{"prompt_tokens":4,"completion_tokens":6,"total_tokens":10}}\n\n`,
        `data: [DONE]\n\n`,
      ]),
      (u) => {
        captured = u;
      },
    );
    await drain(wrapped);
    expect(captured).toEqual({ prompt_tokens: 4, completion_tokens: 6, total_tokens: 10 });
  });
});
