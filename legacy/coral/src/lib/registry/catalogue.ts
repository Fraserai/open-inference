/**
 * The model catalogue: the five open-weight models this product serves.
 *
 * This file describes MODELS, not deployments. Nothing here implies a model is
 * running, available, or Australian — that comes from deployment configuration
 * (see ./deployments.ts) and is evaluated by lib/sovereignty.ts.
 *
 * Deliberately unpopulated fields:
 *   creator, modelVersion, contextWindow
 * We have not been given verified values for these. They are typed, exposed and
 * overridable from environment configuration, but they are NOT guessed. A null
 * here means "we do not know yet", which is the honest answer and is preferable
 * to shipping an invented specification.
 */

/** Where the intelligence scores come from. Displayed wherever a score is shown. */
export const INTELLIGENCE_SCORE_SOURCE = {
  name: "Artificial Analysis",
  url: "https://artificialanalysis.ai",
  /**
   * These are third-party scores republished as catalogue metadata.
   * They are not our benchmark and must never be presented as our measurement.
   */
  disclaimer:
    "Intelligence scores are published by Artificial Analysis and reproduced here as " +
    "catalogue metadata. They are not Coral benchmarks and are not measured by Coral.",
} as const;

export type Modality = "text";

export interface CatalogueModel {
  /** Stable internal identifier. Never exposed to customers; safe to key storage on. */
  internalId: string;
  /** Public API model ID — what the customer puts in the `model` request field. */
  apiModelId: string;
  /** Human-readable name for the website and the models endpoint. */
  displayName: string;
  /** Organisation that created/published the open weights. Null until verified. */
  creator: string | null;
  /** Artificial Analysis Intelligence Score. Third-party metadata — see source above. */
  intelligenceScore: number;
  /** Specific published model version/revision we serve. Null until a deployment pins one. */
  modelVersion: string | null;
  /** Context window in tokens. Null until measured or configured against a real deployment. */
  contextWindow: number | null;
  /** Modalities our API surface accepts for this model today. */
  modalities: Modality[];
}

/**
 * Order is by Artificial Analysis Intelligence Score, descending.
 * These five are the entire MVP catalogue. Adding a sixth is a product decision,
 * not a configuration change.
 */
export const CATALOGUE: readonly CatalogueModel[] = Object.freeze([
  {
    internalId: "kimi-k3",
    apiModelId: "kimi-k3",
    displayName: "Kimi K3",
    creator: null,
    intelligenceScore: 60,
    modelVersion: null,
    contextWindow: null,
    modalities: ["text"],
  },
  {
    internalId: "glm-5-3",
    apiModelId: "glm-5.3",
    displayName: "GLM-5.3",
    creator: null,
    intelligenceScore: 60,
    modelVersion: null,
    contextWindow: null,
    modalities: ["text"],
  },
  {
    internalId: "qwen-3-8",
    apiModelId: "qwen-3.8",
    displayName: "Qwen 3.8",
    creator: null,
    intelligenceScore: 58,
    modelVersion: null,
    contextWindow: null,
    modalities: ["text"],
  },
  {
    internalId: "inkling",
    apiModelId: "inkling",
    displayName: "Inkling",
    creator: null,
    intelligenceScore: 42,
    modelVersion: null,
    contextWindow: null,
    modalities: ["text"],
  },
  {
    internalId: "nemotron-3-ultra",
    apiModelId: "nemotron-3-ultra",
    displayName: "Nemotron 3 Ultra",
    creator: null,
    intelligenceScore: 38,
    modelVersion: null,
    contextWindow: null,
    modalities: ["text"],
  },
]);

/**
 * Environment-variable-safe form of a model's internal id.
 * "glm-5-3" -> "GLM_5_3", used to build CORAL_DEPLOYMENT_GLM_5_3_* names.
 */
export function envKeyFor(internalId: string): string {
  return internalId.replace(/[^a-zA-Z0-9]+/g, "_").toUpperCase();
}

export function findCatalogueModel(apiModelId: string): CatalogueModel | undefined {
  return CATALOGUE.find((m) => m.apiModelId === apiModelId);
}

/** All public model IDs, for validation and documentation. */
export const PUBLIC_MODEL_IDS: readonly string[] = Object.freeze(
  CATALOGUE.map((m) => m.apiModelId),
);
