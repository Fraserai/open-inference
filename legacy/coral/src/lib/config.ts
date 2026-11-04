/**
 * Global application configuration, read from the environment.
 *
 * Every secret and every piece of infrastructure configuration lives here or in
 * the per-deployment configuration. Nothing is hardcoded and nothing is committed.
 */

export const PRODUCT = {
  name: "Coral",
  legalName: "Coral AI",
  tagline: "Australian Sovereign Open Weights Model API",
} as const;

function bool(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined || value.trim() === "") return fallback;
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Development mocks let the API run end to end with no Australian GPU attached.
 * They are refused in production unless someone explicitly opts in, because a
 * mock answering production traffic would be a false sovereignty claim.
 */
export function allowDevelopmentMocks(): boolean {
  return bool(process.env.CORAL_ALLOW_DEVELOPMENT_MOCKS, !isProduction());
}

/** Path to the SQLite database file. */
export function databaseUrl(): string {
  return process.env.DATABASE_URL ?? "./data/coral.db";
}

/** Public base URL, used only for rendering documentation examples. */
export function apiBaseUrl(): string {
  return process.env.CORAL_PUBLIC_API_BASE_URL ?? "http://localhost:3000/v1";
}

/**
 * Customer prompts and model responses are NEVER logged by default.
 * This flag exists so the choice is explicit and auditable, not so it is used.
 * Turning it on in production is a privacy decision requiring customer consent.
 */
export function logRequestContent(): boolean {
  return bool(process.env.CORAL_LOG_REQUEST_CONTENT, false);
}

/** Upstream request timeout in milliseconds. */
export function upstreamTimeoutMs(): number {
  const raw = Number(process.env.CORAL_UPSTREAM_TIMEOUT_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : 300_000;
}
