/**
 * Confirms every one of the five models can be configured as an independent
 * Australian deployment, with its own endpoint, upstream model ID, provider,
 * region, weight location and sovereignty verification — and that no field
 * bleeds between models.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { CATALOGUE, envKeyFor } from "@/lib/registry/catalogue";
import { getDeployment, resetDeploymentCache } from "@/lib/registry/deployments";
import { listPublicModels, resolveModel } from "@/lib/registry";

const saved: Record<string, string | undefined> = {};

function clearCoralEnv() {
  for (const key of Object.keys(process.env)) {
    if (key.startsWith("CORAL_")) delete process.env[key];
  }
  resetDeploymentCache();
}

beforeEach(() => {
  for (const [k, v] of Object.entries(process.env)) {
    if (k.startsWith("CORAL_")) saved[k] = v;
  }
  clearCoralEnv();
});

afterEach(() => {
  clearCoralEnv();
  for (const [k, v] of Object.entries(saved)) if (v !== undefined) process.env[k] = v;
  resetDeploymentCache();
});

/** A distinct, fully-specified Australian deployment per model. */
const FIXTURES = CATALOGUE.map((model, i) => ({
  apiModelId: model.apiModelId,
  key: envKeyFor(model.internalId),
  endpoint: `https://${model.internalId}.au.example.internal/v1`,
  upstreamModelId: `backend/${model.internalId}-internal`,
  provider: ["firmus", "amaze-ai", "sharon-ai", "navigate", "firmus"][i]!,
  region: ["au-syd-1", "au-mel-1", "au-syd-2", "au-per-1", "au-mel-2"][i]!,
  weightLocation: `vault-${i}:au:coral-weights/${model.internalId}`,
  verifiedBy: `ops-${i}@example.com.au`,
  verifiedAt: `2026-09-0${i + 1}`,
  method: `attestation-${i}`,
}));

function configureAll() {
  for (const f of FIXTURES) {
    const p = `CORAL_DEPLOYMENT_${f.key}_`;
    process.env[`${p}ENDPOINT`] = f.endpoint;
    process.env[`${p}UPSTREAM_MODEL_ID`] = f.upstreamModelId;
    process.env[`${p}API_KEY`] = `token-${f.key}`;
    process.env[`${p}INFRASTRUCTURE_PROVIDER`] = f.provider;
    process.env[`${p}INFRASTRUCTURE_REGION`] = f.region;
    process.env[`${p}INFERENCE_COUNTRY`] = "AU";
    process.env[`${p}WEIGHT_COUNTRY`] = "AU";
    process.env[`${p}WEIGHT_LOCATION`] = f.weightLocation;
    process.env[`${p}SOVEREIGNTY_VERIFIED_BY`] = f.verifiedBy;
    process.env[`${p}SOVEREIGNTY_VERIFIED_AT`] = f.verifiedAt;
    process.env[`${p}SOVEREIGNTY_VERIFICATION_METHOD`] = f.method;
  }
  resetDeploymentCache();
}

describe("independent per-model deployment configuration", () => {
  it("configures all five models independently with no cross-contamination", () => {
    configureAll();

    for (const f of FIXTURES) {
      const resolution = resolveModel(f.apiModelId);
      expect(resolution.ok, `${f.apiModelId} should resolve`).toBe(true);
      if (!resolution.ok) continue;

      const d = resolution.deployment;
      expect(d.endpoint).toBe(f.endpoint);
      expect(d.upstreamModelId).toBe(f.upstreamModelId);
      expect(d.upstreamApiKey).toBe(`token-${f.key}`);
      expect(d.claim?.infrastructureProvider).toBe(f.provider);
      expect(d.claim?.infrastructureRegion).toBe(f.region);
      expect(d.claim?.inferenceCountry).toBe("AU");
      expect(d.claim?.weightCountry).toBe("AU");
      expect(d.claim?.weightLocation).toBe(f.weightLocation);
      expect(d.claim?.verification).toEqual({
        verifiedBy: f.verifiedBy,
        verifiedAt: f.verifiedAt,
        method: f.method,
      });
      expect(d.sovereignty.status).toBe("verified");
      expect(d.sovereignty.isSovereign).toBe(true);
    }
  });

  it("gives each model a distinct deployment identity", () => {
    configureAll();
    const ids = FIXTURES.map((f) => getDeployment(f.apiModelId)?.deploymentId);
    expect(new Set(ids).size).toBe(FIXTURES.length);
    expect(ids).not.toContain(undefined);
  });

  it("reports all five as verified Australian sovereign once fully configured", () => {
    configureAll();
    const models = listPublicModels("Coral");
    expect(models).toHaveLength(5);
    expect(models.every((m) => m.sovereignty.australian_sovereign)).toBe(true);
    expect(models.every((m) => m.available)).toBe(true);
  });

  it("leaves unverified metadata null even when a deployment is fully configured", () => {
    configureAll();
    for (const m of listPublicModels("Coral")) {
      expect(m.creator).toBeNull();
      expect(m.model_version).toBeNull();
      expect(m.context_window).toBeNull();
    }
  });

  it("isolates one model's misconfiguration from the other four", () => {
    configureAll();
    process.env.CORAL_DEPLOYMENT_INKLING_INFERENCE_COUNTRY = "SG";
    resetDeploymentCache();

    expect(getDeployment("inkling")?.status).toBe("misconfigured");
    for (const f of FIXTURES.filter((f) => f.apiModelId !== "inkling")) {
      expect(resolveModel(f.apiModelId).ok, `${f.apiModelId} unaffected`).toBe(true);
    }
  });

  it("isolates one model's absence from the other four", () => {
    configureAll();
    for (const k of Object.keys(process.env)) {
      if (k.startsWith("CORAL_DEPLOYMENT_KIMI_K3_")) delete process.env[k];
    }
    resetDeploymentCache();

    expect(resolveModel("kimi-k3").ok).toBe(false);
    for (const f of FIXTURES.filter((f) => f.apiModelId !== "kimi-k3")) {
      expect(resolveModel(f.apiModelId).ok, `${f.apiModelId} unaffected`).toBe(true);
    }
  });
});
