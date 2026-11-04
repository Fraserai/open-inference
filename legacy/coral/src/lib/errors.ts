/**
 * Error responses, in the OpenAI error envelope so existing client libraries
 * surface them correctly:
 *
 *   { "error": { "message", "type", "param", "code" } }
 *
 * Sovereignty failures are deliberately loud and specific. When an Australian
 * deployment cannot serve a request, the customer is told exactly that — and
 * told the request was not sent anywhere else.
 */

export type ErrorType =
  | "invalid_request_error"
  | "authentication_error"
  | "not_found_error"
  | "rate_limit_error"
  | "sovereignty_error"
  | "api_error";

export interface ApiErrorBody {
  error: {
    message: string;
    type: ErrorType;
    param: string | null;
    code: string | null;
  };
}

export function errorBody(
  message: string,
  type: ErrorType,
  code: string | null = null,
  param: string | null = null,
): ApiErrorBody {
  return { error: { message, type, param, code } };
}

export function errorResponse(
  status: number,
  message: string,
  type: ErrorType,
  code: string | null = null,
  param: string | null = null,
  headers: Record<string, string> = {},
): Response {
  return Response.json(errorBody(message, type, code, param), { status, headers });
}
