/**
 * Syncs the model registry into the database.
 *
 * The registry (src/lib/registry) is the source of truth. This mirrors it into
 * the `models` and `model_deployments` tables so usage reporting can join
 * against stable rows. It writes no secrets: endpoints and upstream credentials
 * stay in environment configuration.
 *
 * Idempotent — run it on every deploy.
 */

import { loadEnvFiles } from "@/lib/load-env";

loadEnvFiles();

import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { getDb } from "./client";
import { models, modelDeployments } from "./schema";
import { runMigrations } from "./migrate";
import { CATALOGUE, INTELLIGENCE_SCORE_SOURCE } from "@/lib/registry/catalogue";
import { getDeployments } from "@/lib/registry/deployments";

export function syncRegistryToDatabase(): { models: number; deployments: number } {
  const db = getDb();
  const deployments = getDeployments();
  let deploymentCount = 0;

  for (const model of CATALOGUE) {
    const deployment = deployments.get(model.apiModelId);
    const row = {
      id: model.internalId,
      apiModelId: model.apiModelId,
      displayName: model.displayName,
      creator: deployment?.overrides.creator ?? model.creator,
      intelligenceScore: model.intelligenceScore,
      intelligenceScoreSource: INTELLIGENCE_SCORE_SOURCE.name,
      modelVersion: deployment?.overrides.modelVersion ?? model.modelVersion,
      contextWindow: deployment?.overrides.contextWindow ?? model.contextWindow,
      syncedAt: new Date(),
    };

    db.insert(models)
      .values(row)
      .onConflictDoUpdate({ target: models.id, set: row })
      .run();

    if (!deployment) continue;

    const verification =
      deployment.sovereignty.status === "verified"
        ? deployment.claim?.verification
        : undefined;

    // One deployment row per model in the MVP; replace rather than accumulate.
    db.delete(modelDeployments).where(eq(modelDeployments.modelId, model.internalId)).run();
    db.insert(modelDeployments)
      .values({
        id: randomUUID(),
        modelId: model.internalId,
        infrastructureProvider: deployment.claim?.infrastructureProvider ?? null,
        infrastructureRegion: deployment.claim?.infrastructureRegion ?? null,
        inferenceCountry: deployment.claim?.inferenceCountry ?? null,
        weightCountry: deployment.claim?.weightCountry ?? null,
        weightLocation: deployment.claim?.weightLocation ?? null,
        adapter: deployment.adapter,
        status: deployment.status,
        sovereigntyStatus: deployment.sovereignty.status,
        sovereigntyVerifiedBy: verification?.verifiedBy ?? null,
        sovereigntyVerifiedAt: verification?.verifiedAt ?? null,
        sovereigntyVerificationMethod: verification?.method ?? null,
        syncedAt: new Date(),
      })
      .run();
    deploymentCount += 1;
  }

  return { models: CATALOGUE.length, deployments: deploymentCount };
}

if (process.argv[1] && process.argv[1].endsWith("seed.ts")) {
  runMigrations();
  const result = syncRegistryToDatabase();
  console.log(
    `Registry synced: ${result.models} models, ${result.deployments} deployment records.`,
  );
}
