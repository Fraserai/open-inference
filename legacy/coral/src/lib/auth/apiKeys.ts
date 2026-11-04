/**
 * API key authentication.
 *
 * Keys are high-entropy random tokens, so a single SHA-256 (with an optional
 * server-side pepper) is the appropriate verification method — the slow KDFs
 * that protect low-entropy human passwords buy nothing here and cost latency on
 * every request.
 *
 * The plaintext key exists only at the moment of creation. We store a hash, a
 * non-secret prefix, and the last four characters. A lost key is regenerated,
 * never recovered.
 */

import { createHash, randomBytes, randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { getDb } from "@/lib/db/client";
import { apiKeys, organisations, type ApiKey, type Organisation } from "@/lib/db/schema";

export const KEY_PREFIX = "coral_sk_";
/** Bytes of entropy in the secret portion. 32 bytes = 256 bits. */
const KEY_ENTROPY_BYTES = 32;
/** How much of the key is stored in the clear for identification. */
const PREFIX_DISPLAY_CHARS = 8;

/**
 * Optional pepper, mixed into the hash. Not required, but it means a stolen
 * database alone cannot be used to verify guessed keys.
 *
 * WARNING: changing or losing this value invalidates every existing key.
 */
function pepper(): string {
  return process.env.CORAL_API_KEY_PEPPER ?? "";
}

export function hashApiKey(key: string): string {
  return createHash("sha256").update(`${pepper()}${key}`).digest("hex");
}

export interface GeneratedKey {
  id: string;
  /** Full plaintext key. Show once, then discard. */
  key: string;
  keyPrefix: string;
  keyHash: string;
  lastFour: string;
}

export function generateApiKey(): GeneratedKey {
  const secret = randomBytes(KEY_ENTROPY_BYTES).toString("base64url");
  const key = `${KEY_PREFIX}${secret}`;
  return {
    id: randomUUID(),
    key,
    keyPrefix: `${KEY_PREFIX}${secret.slice(0, PREFIX_DISPLAY_CHARS)}`,
    keyHash: hashApiKey(key),
    lastFour: secret.slice(-4),
  };
}

/** Pull the bearer token out of an Authorization header. */
export function extractBearerToken(header: string | null): string | null {
  if (!header) return null;
  const trimmed = header.trim();
  if (!trimmed.toLowerCase().startsWith("bearer ")) return null;
  const token = trimmed.slice(7).trim();
  return token === "" ? null : token;
}

export interface AuthenticatedCaller {
  apiKey: ApiKey;
  organisation: Organisation;
}

export type AuthResult =
  | { ok: true; caller: AuthenticatedCaller }
  | { ok: false; code: "missing_api_key" | "invalid_api_key" | "organisation_suspended"; message: string };

/** Only bump last_used_at at most once a minute, to keep the write path cheap. */
const LAST_USED_THROTTLE_MS = 60_000;

export function authenticate(authorizationHeader: string | null): AuthResult {
  const token = extractBearerToken(authorizationHeader);
  if (!token) {
    return {
      ok: false,
      code: "missing_api_key",
      message:
        "No API key provided. Send it as an Authorization header: " +
        "`Authorization: Bearer coral_sk_...`.",
    };
  }

  const db = getDb();
  const rows = db
    .select({ key: apiKeys, org: organisations })
    .from(apiKeys)
    .innerJoin(organisations, eq(apiKeys.organisationId, organisations.id))
    .where(and(eq(apiKeys.keyHash, hashApiKey(token)), eq(apiKeys.status, "active")))
    .limit(1)
    .all();

  const row = rows[0];
  if (!row) {
    return { ok: false, code: "invalid_api_key", message: "Invalid API key." };
  }
  if (row.org.status !== "active") {
    return {
      ok: false,
      code: "organisation_suspended",
      message: "This account is suspended.",
    };
  }

  const now = Date.now();
  const last = row.key.lastUsedAt ? row.key.lastUsedAt.getTime() : 0;
  if (now - last > LAST_USED_THROTTLE_MS) {
    db.update(apiKeys)
      .set({ lastUsedAt: new Date(now) })
      .where(eq(apiKeys.id, row.key.id))
      .run();
  }

  return { ok: true, caller: { apiKey: row.key, organisation: row.org } };
}
