# Connecting real Australian model deployments

This procedure turns a model from a development mock into a verified Australian
sovereign deployment. Do it once per model.

Nothing in this repository claims Australian sovereign serving is operational.
Until steps 1–7 are complete for a model, the registry reports it as a mock or
as unconfigured, and the website says so.

---

## Prerequisites (external, not provided by this repo)

- An account with an Australian GPU/AI compute provider — Firmus, Amaze AI,
  Sharon AI or NaviGate.
- Persistent storage in an Australian region for the model weights, separate
  from the GPU worker so it survives the worker being destroyed.
- A host in Australia to run this application.
- TLS certificates and a domain for the public API.

---

## Step 1 — Download the weights yourself

Pull the official open weights from the publisher. Verify the publisher
organisation, not just the model name. Read the LICENSE file in the repository
and confirm it permits hosted commercial serving.

Record the resolved revision and a checksum per file. "Which bytes we hold" is a
different claim from "which revision we asked for", and only the first is
evidence.

## Step 2 — Put the weights on Australian storage

Download directly onto Australian storage where possible. If you stage through a
laptop elsewhere first, the weights were not "downloaded into Australia" — write
down which of the two actually happened, because the claim has to match reality.

Record the precise location, including region, for
`CORAL_DEPLOYMENT_<MODEL>_WEIGHT_LOCATION`.

## Step 3 — Run an OpenAI-compatible server on an Australian GPU

vLLM, SGLang, or anything else exposing `/v1/chat/completions`. Confirm the
instance region is Australian in the provider console — do not infer it from the
region name in a config file.

The server must be reachable from the application host over a private network or
an authenticated HTTPS endpoint. Do not expose a raw inference port publicly.

## Step 4 — Configure the deployment

Fill in the model's block. Using `qwen-3.8` as the example:

```bash
CORAL_DEPLOYMENT_QWEN_3_8_ENDPOINT=https://qwen.au-syd.internal/v1
CORAL_DEPLOYMENT_QWEN_3_8_API_KEY=<provider token>
CORAL_DEPLOYMENT_QWEN_3_8_UPSTREAM_MODEL_ID=<name the backend uses>
CORAL_DEPLOYMENT_QWEN_3_8_INFRASTRUCTURE_PROVIDER=firmus
CORAL_DEPLOYMENT_QWEN_3_8_INFRASTRUCTURE_REGION=au-syd-1
CORAL_DEPLOYMENT_QWEN_3_8_INFERENCE_COUNTRY=AU
CORAL_DEPLOYMENT_QWEN_3_8_WEIGHT_COUNTRY=AU
CORAL_DEPLOYMENT_QWEN_3_8_WEIGHT_LOCATION=firmus:au-syd-1:coral-weight-vault/qwen-3-8
```

Remove `CORAL_DEPLOYMENT_QWEN_3_8_ADAPTER=development-mock`. Its presence
overrides everything above and keeps the model on the mock.

`ENDPOINT` is the OpenAI-compatible **base** URL. The adapter appends
`/chat/completions`, so include `/v1` if your server uses it.

Optional, once known — do not guess these:

```bash
CORAL_DEPLOYMENT_QWEN_3_8_CONTEXT_WINDOW=<measured or documented>
CORAL_DEPLOYMENT_QWEN_3_8_MODEL_VERSION=<revision you actually serve>
CORAL_MODEL_QWEN_3_8_CREATOR=<publisher>
```

## Step 5 — Confirm it routes

```bash
npm run sovereignty:check
```

The model should read `configured_unverified` — Australian configuration
accepted, verification not yet done. If it reads `misconfigured`, the audit
prints the reason.

Then send a real request and check the response headers report
`x-coral-inference-country: AU` and the expected region.

## Step 6 — Verify residency for real

Before recording a verification, establish independently that the machine is in
Australia and the weights are stored in Australia. Acceptable evidence:

- The provider's written attestation or contract schedule naming the region.
- The instance's region and physical data centre in the provider console.
- Network evidence consistent with an Australian endpoint.

Do not verify from the environment variable — the environment variable is the
claim being tested.

## Step 7 — Record the verification

```bash
CORAL_DEPLOYMENT_QWEN_3_8_SOVEREIGNTY_VERIFIED_BY=ops@yourcompany.com.au
CORAL_DEPLOYMENT_QWEN_3_8_SOVEREIGNTY_VERIFIED_AT=2026-09-03
CORAL_DEPLOYMENT_QWEN_3_8_SOVEREIGNTY_VERIFICATION_METHOD=provider attestation + console region + contract schedule 2
```

All three are required; a partial record counts as no verification. Only now does
the model report `australian_sovereign: true`.

Re-run `npm run db:seed` so the database mirror reflects the new state.

---

## Production checklist

- [ ] All five models complete steps 1–7
- [ ] `NODE_ENV=production`
- [ ] `CORAL_ALLOW_DEVELOPMENT_MOCKS` unset or `false`
- [ ] `CORAL_API_KEY_PEPPER` set to a real random value and backed up
      (losing it invalidates every issued key)
- [ ] `DATABASE_URL` on persistent Australian storage, with backups
- [ ] `CORAL_PUBLIC_API_BASE_URL` set to the real domain
- [ ] `npm run sovereignty:check -- --strict` exits zero
- [ ] TLS terminated in front of the application
- [ ] Application host physically in Australia

`--strict` in the deploy pipeline is what stops a build shipping with a mock or
an unverified claim.

---

## Still required beyond this MVP

- Rate limiting and per-organisation quotas
- Billing on top of `usage_events`
- A customer dashboard for self-service key management
- Health probes and alerting on deployment reachability
- Postgres instead of SQLite once write volume justifies it
