/**
 * The model registry: catalogue metadata joined to deployment reality.
 *
 * This is the only place that produces the customer-facing view of a model.
 * It is responsible for making sure infrastructure secrets (upstream endpoints
 * and credentials) never leave the server.
 */

import {
  CATALOGUE,
  INTELLIGENCE_SCORE_SOURCE,
  findCatalogueModel,
  type CatalogueModel,
  type Modality,
} from "./catalogue";
import {
  getDeployment,
  getDeployments,
  isRoutable,
  type DeploymentStatus,
  type ModelDeployment,
} from "./deployments";
import { SOVEREIGNTY_LABELS, type SovereigntyStatus } from "@/lib/sovereignty";

export * from "./catalogue";
export * from "./deployments";

/** Customer-visible model record. Contains no endpoints and no credentials. */
export interface PublicModel {
  id: string;
  object: "model";
  owned_by: string;
  display_name: string;
  creator: string | null;
  intelligence_score: {
    value: number;
    source: string;
    source_url: string;
    note: string;
  };
  model_version: string | null;
  context_window: number | null;
  modalities: Modality[];
  /** Whether a request for this model can be served right now. */
  available: boolean;
  deployment: {
    status: DeploymentStatus;
    infrastructure_provider: string | null;
    infrastructure_region: string | null;
    inference_country: string | null;
    weight_country: string | null;
    weight_location: string | null;
  };
  sovereignty: {
    status: SovereigntyStatus;
    /** True ONLY for a verified Australian deployment. */
    australian_sovereign: boolean;
    label: string;
    verified_at: string | null;
    verified_by: string | null;
    verification_method: string | null;
  };
}

/** Merge catalogue defaults with any per-deployment overrides. */
function resolveMetadata(model: CatalogueModel, d: ModelDeployment | undefined) {
  return {
    creator: d?.overrides.creator ?? model.creator,
    modelVersion: d?.overrides.modelVersion ?? model.modelVersion,
    contextWindow: d?.overrides.contextWindow ?? model.contextWindow,
    modalities: d?.overrides.modalities ?? model.modalities,
  };
}

export function toPublicModel(
  model: CatalogueModel,
  deployment: ModelDeployment | undefined,
  ownedBy: string,
): PublicModel {
  const meta = resolveMetadata(model, deployment);
  const claim = deployment?.claim;
  const sov = deployment?.sovereignty;
  const verification = sov?.status === "verified" ? claim?.verification : undefined;

  return {
    id: model.apiModelId,
    object: "model",
    owned_by: ownedBy,
    display_name: model.displayName,
    creator: meta.creator,
    intelligence_score: {
      value: model.intelligenceScore,
      source: INTELLIGENCE_SCORE_SOURCE.name,
      source_url: INTELLIGENCE_SCORE_SOURCE.url,
      note: INTELLIGENCE_SCORE_SOURCE.disclaimer,
    },
    model_version: meta.modelVersion,
    context_window: meta.contextWindow,
    modalities: meta.modalities,
    available: deployment ? isRoutable(deployment) : false,
    deployment: {
      status: deployment?.status ?? "not_configured",
      infrastructure_provider: claim?.infrastructureProvider || null,
      infrastructure_region: claim?.infrastructureRegion || null,
      inference_country: claim?.inferenceCountry || null,
      weight_country: claim?.weightCountry || null,
      weight_location: claim?.weightLocation || null,
    },
    sovereignty: {
      status: sov?.status ?? "not_configured",
      australian_sovereign: sov?.isSovereign ?? false,
      label: SOVEREIGNTY_LABELS[sov?.status ?? "not_configured"],
      verified_at: verification?.verifiedAt ?? null,
      verified_by: verification?.verifiedBy ?? null,
      verification_method: verification?.method ?? null,
    },
  };
}

export function listPublicModels(ownedBy: string): PublicModel[] {
  const deployments = getDeployments();
  return CATALOGUE.map((m) => toPublicModel(m, deployments.get(m.apiModelId), ownedBy));
}

export function getPublicModel(apiModelId: string, ownedBy: string): PublicModel | undefined {
  const model = findCatalogueModel(apiModelId);
  if (!model) return undefined;
  return toPublicModel(model, getDeployment(apiModelId), ownedBy);
}

export type ResolutionFailure =
  | { ok: false; reason: "unknown_model" }
  | { ok: false; reason: "not_configured" | "misconfigured" | "disabled"; detail: string };

export type Resolution =
  | { ok: true; model: CatalogueModel; deployment: ModelDeployment }
  | ResolutionFailure;

/**
 * Resolve a requested model ID to the single Australian deployment that serves it.
 *
 * There is exactly one candidate. If it cannot serve the request this returns a
 * failure — it does not look for an alternative, and there is no offshore
 * provider it could look for one in.
 */
export function resolveModel(apiModelId: string): Resolution {
  const model = findCatalogueModel(apiModelId);
  if (!model) return { ok: false, reason: "unknown_model" };

  const deployment = getDeployment(apiModelId);
  if (!deployment || deployment.status === "not_configured") {
    return {
      ok: false,
      reason: "not_configured",
      detail: `Model "${apiModelId}" has no Australian deployment configured.`,
    };
  }
  if (deployment.status === "misconfigured") {
    return {
      ok: false,
      reason: "misconfigured",
      detail:
        `Model "${apiModelId}" has a deployment that failed Australian sovereignty ` +
        `validation and will not be used.`,
    };
  }
  if (deployment.status === "disabled") {
    return {
      ok: false,
      reason: "disabled",
      detail: `Model "${apiModelId}" is temporarily disabled.`,
    };
  }
  return { ok: true, model, deployment };
}
