/**
 * Request validation for /v1/chat/completions.
 *
 * Validation is intentionally permissive about parameters we do not interpret:
 * unknown keys are passed through to the Australian inference server so that
 * engine-specific options keep working. What we do enforce is the shape the
 * router depends on — a known model ID and a non-empty message list.
 */

import { z } from "zod";
import { PUBLIC_MODEL_IDS } from "@/lib/registry/catalogue";

const contentSchema = z.union([
  z.string(),
  z.array(z.unknown()),
  z.null(),
]);

const messageSchema = z.object({
  role: z.enum(["system", "user", "assistant", "tool", "developer"]),
  content: contentSchema,
  name: z.string().optional(),
  tool_call_id: z.string().optional(),
});

export const chatCompletionSchema = z
  .object({
    model: z.string().min(1, "model is required"),
    messages: z.array(messageSchema).min(1, "messages must contain at least one message"),
    stream: z.boolean().optional(),
    max_tokens: z.number().int().positive().optional(),
    max_completion_tokens: z.number().int().positive().optional(),
    temperature: z.number().min(0).max(2).optional(),
    top_p: z.number().min(0).max(1).optional(),
    n: z.number().int().positive().max(8).optional(),
    stop: z.union([z.string(), z.array(z.string()).max(4)]).optional(),
    presence_penalty: z.number().min(-2).max(2).optional(),
    frequency_penalty: z.number().min(-2).max(2).optional(),
    seed: z.number().int().optional(),
    user: z.string().optional(),
  })
  .loose();

export type ValidationIssue = { message: string; param: string | null };

export function firstIssue(error: z.ZodError): ValidationIssue {
  const issue = error.issues[0];
  if (!issue) return { message: "Invalid request body.", param: null };
  const param = issue.path.length > 0 ? issue.path.join(".") : null;
  return { message: issue.message, param };
}

/** Model IDs are validated against the registry so the error can list the real five. */
export function unknownModelMessage(requested: string): string {
  return (
    `The model "${requested}" does not exist. ` +
    `Available models: ${PUBLIC_MODEL_IDS.join(", ")}.`
  );
}
