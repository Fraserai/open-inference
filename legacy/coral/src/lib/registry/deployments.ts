/**
 * Model deployments, loaded from environment configuration.
 *
 * A catalogue entry is a product fact. A deployment is an infrastructure fact:
 * a specific model running on a specific Australian machine behind a specific
 * endpoint. One catalogue model has at most one deployment in the MVP.
 *
 * THE OFFSHORE GATE
 * -----------------
 * A deployment whose configuration does not assert Australian inference AND
 * Australian weight storage is marked `misconfigured` and is never returned as
 * routable. There is no second choice, no fallback list and no "nearest region"
 * behaviour anywhere in this module. If Australia is unavailable, the request
 * fails. That is the product.
 */

import {
  CATALOGUE,
  envKeyFor,
  type CatalogueModel,
  type Modality,
} from "./catalogue";
import {
  evaluateSovereignty,
  validateAustralianClaim,
  isCompleteVerification,
  type SovereigntyClaim,
  type SovereigntyEvaluation,
  type SovereigntyVerification,
} from "@/lib/sovereignty";
import { allowDevelopmentMocks } from "@/lib/config";

/** Which adapter talks to this deployment. */
export type AdapterKind = "openai-compatible" | "development-mock";

export type DeploymentStatus =
  /** No CORAL_DEPLOYMENT_<MODEL>_* configuration present. */
  | "not_configured"
  /** Configuration present but invalid or non-Australian. Never routable. */
  | "misconfigured"
  /** A development mock is standing in for real Australian infrastructure. */
  | "development_mock"
  /** Configured, Australian, and routable. */
  | "active"
  /** Configured and valid, but deliberately switched off. */
  | "disabled";

export interface ModelDeployment {
  deploymentId: string;
  internalId: string;
  apiModelId: string;
  adapter: AdapterKind;
  /** Upstream base URL. INTERNAL ONLY — never serialised to a customer response. */
  endpoint: string | null;
  /** Credential for the upstream. INTERNAL ONLY — never serialised, never logged. */
  upstreamApiKey: string | null;
  /** The model name the Australian backend itself expects, which may differ from ours. */
  upstreamModelId: string;
  claim?: SovereigntyClaim;
  sovereignty: SovereigntyEvaluation;
  status: DeploymentStatus;
  /** Why this deployment is not usable, if it is not. */
  configErrors: string[];
  /** Per-deployment overrides of catalogue metadata we do not know up front. */
  overrides: {
    creator: string | null;
    modelVersion: string | null;
    contextWindow: number | null;
    modalities: Modality[] | null;
  };
}

function env(name: string): string | undefined {
  const v = process.env[name];
  return v === undefined || v.trim() === "" ? undefined : v.trim();
}

function envNumber(name: string): number | null {
  const raw = env(name);
  if (raw === undefined) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function envBool(name: string, fallback: boolean): boolean {
  const raw = env(name);
  if (raw === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

function parseModalities(name: string): Modality[] | null {
  const raw = env(name);
  if (!raw) return null;
  const parts = raw
    .split(",")
    .map((p) => p.trim().toLowerCase())
    .filter((p): p is Modality => p === "text");
  return parts.length > 0 ? parts : null;
}

/** Build one deployment from `CORAL_DEPLOYMENT_<KEY>_*` environment variables. */
function loadDeployment(model: CatalogueModel): ModelDeployment {
  const key = envKeyFor(model.internalId);
  const p = `CORAL_DEPLOYMENT_${key}_`;

  const overrides = {
    creator: env(`CORAL_MODEL_${key}_CREATOR`) ?? null,
    modelVersion: env(`${p}MODEL_VERSION`) ?? null,
    contextWindow: envNumber(`${p}CONTEXT_WINDOW`),
    modalities: parseModalities(`${p}MODALITIES`),
  };

  const base = {
    internalId: model.internalId,
    apiModelId: model.apiModelId,
    upstreamModelId: env(`${p}UPSTREAM_MODEL_ID`) ?? model.apiModelId,
    overrides,
  };

  const adapterRaw = (env(`${p}ADAPTER`) ?? "").toLowerCase();
  const isMock = adapterRaw === "development-mock" || adapterRaw === "mock";

  // ---- development mock -------------------------------------------------
  if (isMock) {
    const permitted = allowDevelopmentMocks();
    const sovereignty = evaluateSovereignty(undefined, true);
    return {
      ...base,
      deploymentId: `${model.internalId}@development-mock`,
      adapter: "development-mock",
      endpoint: null,
      upstreamApiKey: null,
      sovereignty,
      status: permitted ? "development_mock" : "misconfigured",
      configErrors: permitted
        ? []
        : [
            "development mock configured while CORAL_ALLOW_DEVELOPMENT_MOCKS is off " +
              "(mocks are refused in production)",
          ],
    };
  }

  const endpoint = env(`${p}ENDPOINT`);

  // ---- nothing configured ----------------------------------------------
  if (!endpoint) {
    return {
      ...base,
      deploymentId: `${model.internalId}@unconfigured`,
      adapter: "openai-compatible",
      endpoint: null,
      upstreamApiKey: null,
      sovereignty: evaluateSovereignty(undefined, false),
      status: "not_configured",
      configErrors: [`${p}ENDPOINT is not set`],
    };
  }

  const verification: SovereigntyVerification = {
    verifiedBy: env(`${p}SOVEREIGNTY_VERIFIED_BY`) ?? "",
    verifiedAt: env(`${p}SOVEREIGNTY_VERIFIED_AT`) ?? "",
    method: env(`${p}SOVEREIGNTY_VERIFICATION_METHOD`) ?? "",
  };

  const claim: SovereigntyClaim = {
    inferenceCountry: env(`${p}INFERENCE_COUNTRY`) ?? "",
    weightCountry: env(`${p}WEIGHT_COUNTRY`) ?? "",
    infrastructureRegion: env(`${p}INFRASTRUCTURE_REGION`) ?? "",
    infrastructureProvider: env(`${p}INFRASTRUCTURE_PROVIDER`) ?? "",
    weightLocation: env(`${p}WEIGHT_LOCATION`) ?? "",
    verification: isCompleteVerification(verification) ? verification : undefined,
  };

  const configErrors = validateAustralianClaim(claim);
  const sovereignty = evaluateSovereignty(claim, false);

  let endpointUrl: URL | null = null;
  try {
    endpointUrl = new URL(endpoint);
  } catch {
    configErrors.push(`${p}ENDPOINT is not a valid URL`);
  }
  if (endpointUrl && !["http:", "https:"].includes(endpointUrl.protocol)) {
    configErrors.push(`${p}ENDPOINT must be http or https`);
  }

  const enabled = envBool(`${p}ENABLED`, true);

  let status: DeploymentStatus;
  if (configErrors.length > 0) {
    // Non-Australian or broken configuration. Never routable.
    status = "misconfigured";
  } else if (!enabled) {
    status = "disabled";
  } else {
    status = "active";
  }

  return {
    ...base,
    deploymentId:
      env(`${p}DEPLOYMENT_ID`) ??
      `${model.internalId}@${claim.infrastructureProvider || "unknown"}-${
        claim.infrastructureRegion || "unknown"
      }`,
    adapter: "openai-compatible",
    endpoint,
    upstreamApiKey: env(`${p}API_KEY`) ?? null,
    claim,
    sovereignty,
    status,
    configErrors,
  };
}

let cache: Map<string, ModelDeployment> | null = null;

export function loadAllDeployments(): Map<string, ModelDeployment> {
  const map = new Map<string, ModelDeployment>();
  for (const model of CATALOGUE) {
    map.set(model.apiModelId, loadDeployment(model));
  }
  return map;
}

export function getDeployments(): Map<string, ModelDeployment> {
  if (!cache) cache = loadAllDeployments();
  return cache;
}

/** Test/CLI helper — forces deployment configuration to be re-read. */
export function resetDeploymentCache(): void {
  cache = null;
}

export function getDeployment(apiModelId: string): ModelDeployment | undefined {
  return getDeployments().get(apiModelId);
}

/**
 * A deployment may serve traffic only when it is `active` (verified Australian
 * infrastructure or configured-and-pending) or an explicitly permitted
 * development mock. Everything else fails the request.
 */
export function isRoutable(d: ModelDeployment): boolean {
  return d.status === "active" || d.status === "development_mock";
}
