/**
 * Adapter selection.
 *
 * The adapter is chosen from the deployment's own configuration. There is no
 * fallback chain: an unroutable deployment produces an error, not a different
 * adapter pointed somewhere else.
 */

import type { ModelDeployment } from "@/lib/registry/deployments";
import { DevelopmentMockAdapter } from "./development-mock";
import { OpenAiCompatibleAdapter } from "./openai-compatible";
import type { ComputeAdapter } from "./types";

export * from "./types";
export { OpenAiCompatibleAdapter } from "./openai-compatible";
export { DevelopmentMockAdapter, MOCK_NOTICE } from "./development-mock";

const openAiCompatible = new OpenAiCompatibleAdapter();
const developmentMock = new DevelopmentMockAdapter();

export function adapterFor(deployment: ModelDeployment): ComputeAdapter {
  switch (deployment.adapter) {
    case "development-mock":
      return developmentMock;
    case "openai-compatible":
      return openAiCompatible;
  }
}
