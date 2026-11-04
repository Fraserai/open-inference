/**
 * Shared per-request plumbing for the /v1 routes.
 */

import { randomUUID } from "node:crypto";
import { authenticate, type AuthenticatedCaller } from "@/lib/auth/apiKeys";
import { ensureDatabase } from "@/lib/db/bootstrap";
import { errorResponse } from "@/lib/errors";

export interface RequestContext {
  requestId: string;
  startedAt: number;
}

export function newContext(): RequestContext {
  return { requestId: randomUUID(), startedAt: Date.now() };
}

export function elapsedMs(ctx: RequestContext): number {
  return Date.now() - ctx.startedAt;
}

export type Authorised =
  | { ok: true; caller: AuthenticatedCaller }
  | { ok: false; response: Response; code: string };

export function requireApiKey(request: Request, ctx: RequestContext): Authorised {
  ensureDatabase();
  const result = authenticate(request.headers.get("authorization"));
  if (result.ok) return { ok: true, caller: result.caller };

  return {
    ok: false,
    code: result.code,
    response: errorResponse(
      401,
      result.message,
      "authentication_error",
      result.code,
      null,
      { "x-request-id": ctx.requestId },
    ),
  };
}
