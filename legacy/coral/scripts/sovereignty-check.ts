/**
 * Sovereignty audit.
 *
 *   npm run sovereignty:check           report the posture
 *   npm run sovereignty:check -- --strict   exit non-zero unless all five models
 *                                           are verified Australian
 *
 * Run --strict in the production deploy pipeline. It is the gate that stops a
 * build shipping with a mock, a misconfiguration, or an unverified claim.
 */

import { loadEnvFiles } from "@/lib/load-env";

loadEnvFiles();

import { CATALOGUE } from "@/lib/registry/catalogue";
import { getDeployments } from "@/lib/registry/deployments";
import { SOVEREIGNTY_LABELS } from "@/lib/sovereignty";
import { allowDevelopmentMocks, isProduction } from "@/lib/config";

const strict = process.argv.includes("--strict");
const deployments = getDeployments();

console.log("Australian sovereignty audit");
console.log("============================");
console.log(`NODE_ENV                : ${process.env.NODE_ENV ?? "development"}`);
console.log(`Development mocks       : ${allowDevelopmentMocks() ? "PERMITTED" : "refused"}`);
console.log(`Offshore fallback       : none (not implemented)`);
console.log("");

let verified = 0;
let problems = 0;

for (const model of CATALOGUE) {
  const d = deployments.get(model.apiModelId);
  const status = d?.sovereignty.status ?? "not_configured";
  const mark = status === "verified" ? "PASS" : status === "development_mock" ? "MOCK" : "FAIL";
  if (status === "verified") verified += 1;
  else problems += 1;

  console.log(`[${mark}] ${model.displayName} (${model.apiModelId})`);
  console.log(`       deployment      : ${d?.deploymentId ?? "-"}`);
  console.log(`       deploy status   : ${d?.status ?? "not_configured"}`);
  console.log(`       sovereignty     : ${SOVEREIGNTY_LABELS[status]}`);
  console.log(`       provider/region : ${d?.claim?.infrastructureProvider ?? "-"} / ${d?.claim?.infrastructureRegion ?? "-"}`);
  console.log(`       inference / weights: ${d?.claim?.inferenceCountry ?? "-"} / ${d?.claim?.weightCountry ?? "-"}`);
  for (const reason of d?.sovereignty.reasons ?? ["no deployment configured"]) {
    console.log(`       ! ${reason}`);
  }
  for (const err of d?.configErrors ?? []) {
    console.log(`       ! config: ${err}`);
  }
  console.log("");
}

console.log(`Verified Australian sovereign: ${verified}/${CATALOGUE.length}`);

if (isProduction() && allowDevelopmentMocks()) {
  console.error("\nERROR: development mocks are permitted while NODE_ENV=production.");
  process.exit(1);
}

if (strict && problems > 0) {
  console.error(
    `\nERROR: --strict requires all ${CATALOGUE.length} models to be verified Australian ` +
      `deployments. ${problems} are not.`,
  );
  process.exit(1);
}
