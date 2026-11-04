/**
 * MVP data model.
 *
 * PRIVACY BOUNDARY: there is no column anywhere in this schema for prompt text,
 * completion text, or message content. Usage events record operational metadata
 * only — who called, which model, which deployment, how many tokens, how long,
 * and whether it succeeded. Customer content is never persisted.
 */

import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

/** The customer. One organisation owns many API keys. */
export const organisations = sqliteTable("organisations", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  slug: text("slug").notNull().unique(),
  /** Billing/registration country. Our customers are Australian businesses. */
  country: text("country").notNull().default("AU"),
  /** Australian Business Number, when supplied. */
  abn: text("abn"),
  contactEmail: text("contact_email"),
  status: text("status", { enum: ["active", "suspended"] })
    .notNull()
    .default("active"),
  createdAt: integer("created_at", { mode: "timestamp_ms" })
    .notNull()
    .default(sql`(unixepoch() * 1000)`),
});

/**
 * API keys.
 * The plaintext key is shown once at creation and never stored. We keep a
 * SHA-256 hash for verification, a prefix for O(1) lookup, and the last four
 * characters so a customer can identify a key in a list.
 */
export const apiKeys = sqliteTable(
  "api_keys",
  {
    id: text("id").primaryKey(),
    organisationId: text("organisation_id")
      .notNull()
      .references(() => organisations.id),
    name: text("name").notNull(),
    /** Non-secret leading segment, e.g. "coral_sk_a1b2c3d4". Indexed for lookup. */
    keyPrefix: text("key_prefix").notNull(),
    /** SHA-256 (optionally peppered) of the full key. Never reversible. */
    keyHash: text("key_hash").notNull(),
    lastFour: text("last_four").notNull(),
    status: text("status", { enum: ["active", "revoked"] })
      .notNull()
      .default("active"),
    createdAt: integer("created_at", { mode: "timestamp_ms" })
      .notNull()
      .default(sql`(unixepoch() * 1000)`),
    lastUsedAt: integer("last_used_at", { mode: "timestamp_ms" }),
    revokedAt: integer("revoked_at", { mode: "timestamp_ms" }),
  },
  (t) => [
    index("api_keys_prefix_idx").on(t.keyPrefix),
    uniqueIndex("api_keys_hash_idx").on(t.keyHash),
    index("api_keys_org_idx").on(t.organisationId),
  ],
);

/**
 * Catalogue mirror. The registry in src/lib/registry is the source of truth;
 * this table exists so usage events have a stable model reference and so
 * reporting can join without reading application code.
 */
export const models = sqliteTable("models", {
  /** Matches CatalogueModel.internalId. */
  id: text("id").primaryKey(),
  apiModelId: text("api_model_id").notNull().unique(),
  displayName: text("display_name").notNull(),
  creator: text("creator"),
  /** Artificial Analysis Intelligence Score — third-party metadata, not our benchmark. */
  intelligenceScore: integer("intelligence_score").notNull(),
  intelligenceScoreSource: text("intelligence_score_source")
    .notNull()
    .default("Artificial Analysis"),
  modelVersion: text("model_version"),
  contextWindow: integer("context_window"),
  syncedAt: integer("synced_at", { mode: "timestamp_ms" })
    .notNull()
    .default(sql`(unixepoch() * 1000)`),
});

/**
 * A model running on specific Australian infrastructure.
 *
 * NOTE: upstream endpoints and provider credentials are deliberately NOT stored
 * here. They live in environment configuration only. This table records the
 * non-secret sovereignty facts so they can be audited and reported on.
 */
export const modelDeployments = sqliteTable(
  "model_deployments",
  {
    id: text("id").primaryKey(),
    modelId: text("model_id")
      .notNull()
      .references(() => models.id),
    infrastructureProvider: text("infrastructure_provider"),
    infrastructureRegion: text("infrastructure_region"),
    inferenceCountry: text("inference_country"),
    weightCountry: text("weight_country"),
    weightLocation: text("weight_location"),
    adapter: text("adapter").notNull(),
    status: text("status").notNull(),
    sovereigntyStatus: text("sovereignty_status").notNull(),
    sovereigntyVerifiedBy: text("sovereignty_verified_by"),
    sovereigntyVerifiedAt: text("sovereignty_verified_at"),
    sovereigntyVerificationMethod: text("sovereignty_verification_method"),
    syncedAt: integer("synced_at", { mode: "timestamp_ms" })
      .notNull()
      .default(sql`(unixepoch() * 1000)`),
  },
  (t) => [index("model_deployments_model_idx").on(t.modelId)],
);

/**
 * One row per API request. Operational metadata only — see the privacy note at
 * the top of this file. This is the foundation for billing and for operational
 * visibility, and nothing here identifies what a customer asked.
 */
export const usageEvents = sqliteTable(
  "usage_events",
  {
    id: text("id").primaryKey(),
    /** Correlates with the x-request-id header returned to the customer. */
    requestId: text("request_id").notNull(),
    organisationId: text("organisation_id").references(() => organisations.id),
    apiKeyId: text("api_key_id").references(() => apiKeys.id),
    /** Public model ID requested. Kept as text so events survive catalogue edits. */
    apiModelId: text("api_model_id"),
    deploymentId: text("deployment_id"),
    infrastructureProvider: text("infrastructure_provider"),
    infrastructureRegion: text("infrastructure_region"),
    inferenceCountry: text("inference_country"),
    streamed: integer("streamed", { mode: "boolean" }).notNull().default(false),
    promptTokens: integer("prompt_tokens"),
    completionTokens: integer("completion_tokens"),
    totalTokens: integer("total_tokens"),
    latencyMs: integer("latency_ms").notNull(),
    statusCode: integer("status_code").notNull(),
    /** Machine-readable error code when the request failed. No error content. */
    errorCode: text("error_code"),
    createdAt: integer("created_at", { mode: "timestamp_ms" })
      .notNull()
      .default(sql`(unixepoch() * 1000)`),
  },
  (t) => [
    index("usage_events_org_idx").on(t.organisationId),
    index("usage_events_created_idx").on(t.createdAt),
    index("usage_events_model_idx").on(t.apiModelId),
  ],
);

export type Organisation = typeof organisations.$inferSelect;
export type ApiKey = typeof apiKeys.$inferSelect;
export type UsageEvent = typeof usageEvents.$inferInsert;
