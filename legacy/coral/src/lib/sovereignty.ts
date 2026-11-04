/**
 * Australian sovereignty rules.
 *
 * Sovereignty is a technical property of a *deployment*, never of a catalogue
 * entry. A model existing in the registry says nothing about where it runs.
 * The only way a model reaches `verified` is if a deployment was configured
 * with Australian inference and weight storage AND a human recorded a
 * verification against it.
 *
 * These functions are the single place that decides what may be presented as
 * Australian sovereign. Nothing else in the codebase should make that claim.
 */

/** ISO 3166-1 alpha-2 for Australia. The only country we will serve from. */
export const REQUIRED_COUNTRY = "AU" as const;

export type SovereigntyStatus =
  /** No deployment configured for this model at all. */
  | "not_configured"
  /** A local development mock is serving this model. Never a sovereignty claim. */
  | "development_mock"
  /** AU deployment configured, but nobody has verified it yet. */
  | "configured_unverified"
  /** AU deployment configured and verification recorded. Only this may be shown as sovereign. */
  | "verified";

/**
 * Evidence that a human checked the deployment really is where it claims to be.
 * All three fields are required — a half-filled record is not a verification.
 */
export interface SovereigntyVerification {
  /** Who performed the verification. */
  verifiedBy: string;
  /** ISO 8601 date the verification was performed. */
  verifiedAt: string;
  /** How it was verified, e.g. "provider attestation + traceroute + contract schedule 2". */
  method: string;
}

export interface SovereigntyClaim {
  /** Country where inference executes. Must be AU for a real deployment. */
  inferenceCountry: string;
  /** Country where the model weights are stored at rest. Must be AU. */
  weightCountry: string;
  /** Provider-specific region identifier, e.g. "au-syd-1". Free text — providers differ. */
  infrastructureRegion: string;
  /** Australian compute provider, e.g. "firmus". */
  infrastructureProvider: string;
  /** Precise description of where the weights sit, e.g. "firmus:au-syd-1:coral-weight-vault". */
  weightLocation: string;
  /** Present only when a verification has actually been performed. */
  verification?: SovereigntyVerification;
}

export interface SovereigntyEvaluation {
  status: SovereigntyStatus;
  /** True only when status === "verified". The single flag the UI/API may trust. */
  isSovereign: boolean;
  /** Human-readable reasons this deployment is not verified. Empty when verified. */
  reasons: string[];
}

/** A country field is acceptable only if it is exactly AU (case-insensitive). */
export function isAustralian(country: string | undefined | null): boolean {
  return typeof country === "string" && country.trim().toUpperCase() === REQUIRED_COUNTRY;
}

/**
 * Hard gate applied when loading deployment configuration.
 *
 * A deployment that does not assert Australian inference *and* Australian
 * weight storage is rejected outright — it is never registered, so the router
 * can never reach it. This is the control that makes offshore routing
 * impossible rather than merely discouraged.
 */
export function validateAustralianClaim(claim: SovereigntyClaim): string[] {
  const errors: string[] = [];
  if (!isAustralian(claim.inferenceCountry)) {
    errors.push(
      `inference country is "${claim.inferenceCountry}", must be ${REQUIRED_COUNTRY}`,
    );
  }
  if (!isAustralian(claim.weightCountry)) {
    errors.push(
      `model weight country is "${claim.weightCountry}", must be ${REQUIRED_COUNTRY}`,
    );
  }
  if (!claim.infrastructureRegion.trim()) {
    errors.push("infrastructure region is empty");
  }
  if (!claim.infrastructureProvider.trim()) {
    errors.push("infrastructure provider is empty");
  }
  if (!claim.weightLocation.trim()) {
    errors.push("weight location is empty");
  }
  return errors;
}

/** A verification record counts only when all three fields are non-empty. */
export function isCompleteVerification(
  v: SovereigntyVerification | undefined,
): v is SovereigntyVerification {
  return Boolean(v && v.verifiedBy.trim() && v.verifiedAt.trim() && v.method.trim());
}

/**
 * Decide the sovereignty status of a configured deployment.
 * `isDevelopmentMock` short-circuits everything: a mock is never sovereign,
 * regardless of what its configuration claims.
 */
export function evaluateSovereignty(
  claim: SovereigntyClaim | undefined,
  isDevelopmentMock: boolean,
): SovereigntyEvaluation {
  if (isDevelopmentMock) {
    return {
      status: "development_mock",
      isSovereign: false,
      reasons: ["served by a local development mock, not Australian infrastructure"],
    };
  }
  if (!claim) {
    return {
      status: "not_configured",
      isSovereign: false,
      reasons: ["no deployment configured"],
    };
  }

  const claimErrors = validateAustralianClaim(claim);
  if (claimErrors.length > 0) {
    return { status: "not_configured", isSovereign: false, reasons: claimErrors };
  }
  if (!isCompleteVerification(claim.verification)) {
    return {
      status: "configured_unverified",
      isSovereign: false,
      reasons: [
        "Australian deployment configured but sovereignty has not been verified " +
          "(requires verified_by, verified_at and method)",
      ],
    };
  }
  return { status: "verified", isSovereign: true, reasons: [] };
}

/** Wording used consistently across the API and the website. */
export const SOVEREIGNTY_LABELS: Record<SovereigntyStatus, string> = {
  not_configured: "Not configured",
  development_mock: "Development mock — not sovereign",
  configured_unverified: "Australian deployment configured — verification pending",
  verified: "Australian sovereign — verified",
};
