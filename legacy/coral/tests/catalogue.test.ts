import { describe, expect, it } from "vitest";
import { CATALOGUE, PUBLIC_MODEL_IDS, envKeyFor } from "@/lib/registry/catalogue";

describe("model catalogue", () => {
  it("contains exactly the five MVP models", () => {
    expect(CATALOGUE).toHaveLength(5);
    expect(PUBLIC_MODEL_IDS).toEqual([
      "kimi-k3",
      "glm-5.3",
      "qwen-3.8",
      "inkling",
      "nemotron-3-ultra",
    ]);
  });

  it("carries the Artificial Analysis intelligence scores exactly as supplied", () => {
    const scores = Object.fromEntries(
      CATALOGUE.map((m) => [m.apiModelId, m.intelligenceScore]),
    );
    expect(scores).toEqual({
      "kimi-k3": 60,
      "glm-5.3": 60,
      "qwen-3.8": 58,
      inkling: 42,
      "nemotron-3-ultra": 38,
    });
  });

  it("does not fabricate unknown technical metadata", () => {
    for (const model of CATALOGUE) {
      expect(model.creator).toBeNull();
      expect(model.modelVersion).toBeNull();
      expect(model.contextWindow).toBeNull();
    }
  });

  it("derives stable environment keys from internal ids", () => {
    expect(envKeyFor("kimi-k3")).toBe("KIMI_K3");
    expect(envKeyFor("glm-5-3")).toBe("GLM_5_3");
    expect(envKeyFor("nemotron-3-ultra")).toBe("NEMOTRON_3_ULTRA");
  });
});
