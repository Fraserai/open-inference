/**
 * The tests that matter most: proving there is no offshore path.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetDeploymentCache, getDeployment, isRoutable } from "@/lib/registry/deployments";
import { resolveModel, listPublicModels } from "@/lib/registry";

const CORAL_ENV = /^CORAL_/;
let saved: Record<string, string | undefined> = {};

function clearCoralEnv() {
  for (const key of Object.keys(process.env)) {
    if (CORAL_ENV.test(key)) delete process.env[key];
  }
  resetDeploymentCache();
}

beforeEach(() => {
  saved = { ...process.env } as Record<string, string | undefined>;
  clearCoralEnv();
});

afterEach(() => {
  for (const key of Object.keys(process.env)) {
    if (CORAL_ENV.test(key)) delete process.env[key];
  }
  for (const [k, v] of Object.entries(saved)) {
    if (CORAL_ENV.test(k) && v !== undefined) process.env[k] = v;
  }
  resetDeploymentCache();
});

function configureKimi(overrides: Record<string, string> = {}) {
  const base: Record<string, string> = {
    CORAL_DEPLOYMENT_KIMI_K3_ENDPOINT: "https://kimi.au-syd.internal/v1",
    CORAL_DEPLOYMENT_KIMI_K3_INFERENCE_COUNTRY: "AU",
    CORAL_DEPLOYMENT_KIMI_K3_WEIGHT_COUNTRY: "AU",
    CORAL_DEPLOYMENT_KIMI_K3_INFRASTRUCTURE_REGION: "au-syd-1",
    CORAL_DEPLOYMENT_KIMI_K3_INFRASTRUCTURE_PROVIDER: "firmus",
    CORAL_DEPLOYMENT_KIMI_K3_WEIGHT_LOCATION: "firmus:au-syd-1:vault/kimi-k3",
  };
  for (const [k, v] of Object.entries({ ...base, ...overrides })) process.env[k] = v;
  resetDeploymentCache();
}

describe("routing and the offshore gate", () => {
  it("rejects an unknown model rather than substituting one", () => {
    const result = resolveModel("gpt-4o");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("unknown_model");
  });

  it("fails closed when no deployment is configured", () => {
    const result = resolveModel("kimi-k3");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("not_configured");
  });

  it("refuses to register a deployment whose inference country is not AU", () => {
    configureKimi({ CORAL_DEPLOYMENT_KIMI_K3_INFERENCE_COUNTRY: "US" });
    const deployment = getDeployment("kimi-k3");
    expect(deployment?.status).toBe("misconfigured");
    expect(isRoutable(deployment!)).toBe(false);

    const result = resolveModel("kimi-k3");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("misconfigured");
  });

  it("refuses to register a deployment whose weights are stored offshore", () => {
    configureKimi({ CORAL_DEPLOYMENT_KIMI_K3_WEIGHT_COUNTRY: "US" });
    expect(getDeployment("kimi-k3")?.status).toBe("misconfigured");
  });

  it("routes to a valid Australian deployment", () => {
    configureKimi();
    const result = resolveModel("kimi-k3");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.deployment.endpoint).toBe("https://kimi.au-syd.internal/v1");
      expect(result.deployment.claim?.inferenceCountry).toBe("AU");
      expect(result.deployment.sovereignty.status).toBe("configured_unverified");
    }
  });

  it("does not borrow another model's deployment when one model is unconfigured", () => {
    configureKimi();
    // GLM has no deployment. It must fail, not inherit Kimi's Australian endpoint.
    const glm = resolveModel("glm-5.3");
    expect(glm.ok).toBe(false);
    if (!glm.ok) expect(glm.reason).toBe("not_configured");
  });

  it("honours an explicit disable without falling through to anything else", () => {
    configureKimi({ CORAL_DEPLOYMENT_KIMI_K3_ENABLED: "false" });
    const result = resolveModel("kimi-k3");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("disabled");
  });

  it("never leaks upstream endpoints or credentials in the public model list", () => {
    configureKimi({ CORAL_DEPLOYMENT_KIMI_K3_API_KEY: "super-secret-provider-token" });
    const serialised = JSON.stringify(listPublicModels("Coral"));
    expect(serialised).not.toContain("super-secret-provider-token");
    expect(serialised).not.toContain("kimi.au-syd.internal");
  });

  it("reports sovereign only once verification is recorded", () => {
    configureKimi();
    expect(listPublicModels("Coral")[0]?.sovereignty.australian_sovereign).toBe(false);

    configureKimi({
      CORAL_DEPLOYMENT_KIMI_K3_SOVEREIGNTY_VERIFIED_BY: "ops@example.com",
      CORAL_DEPLOYMENT_KIMI_K3_SOVEREIGNTY_VERIFIED_AT: "2026-09-01",
      CORAL_DEPLOYMENT_KIMI_K3_SOVEREIGNTY_VERIFICATION_METHOD: "site attestation",
    });
    const model = listPublicModels("Coral")[0];
    expect(model?.sovereignty.status).toBe("verified");
    expect(model?.sovereignty.australian_sovereign).toBe(true);
  });

  it("marks development mocks as mocks, never as sovereign", () => {
    process.env.CORAL_ALLOW_DEVELOPMENT_MOCKS = "true";
    process.env.CORAL_DEPLOYMENT_INKLING_ADAPTER = "development-mock";
    resetDeploymentCache();

    const deployment = getDeployment("inkling");
    expect(deployment?.status).toBe("development_mock");
    expect(deployment?.sovereignty.isSovereign).toBe(false);
    expect(isRoutable(deployment!)).toBe(true);
  });

  it("refuses development mocks when they are not permitted", () => {
    process.env.CORAL_ALLOW_DEVELOPMENT_MOCKS = "false";
    process.env.CORAL_DEPLOYMENT_INKLING_ADAPTER = "development-mock";
    resetDeploymentCache();

    const deployment = getDeployment("inkling");
    expect(deployment?.status).toBe("misconfigured");
    expect(isRoutable(deployment!)).toBe(false);
  });
});
