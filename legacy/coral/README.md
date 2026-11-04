# Coral — Australian Sovereign Open Weights Model API

Five open-weight models. Weights stored in Australia, inference on Australian
compute, served to Australian businesses and enterprises through one
OpenAI-compatible API.

**There is no offshore fallback.** If an Australian deployment cannot serve a
request, the request fails with a clear error. That is a product requirement,
enforced in code, and it is tested.

---

## The catalogue

| API model ID | Model | Artificial Analysis Intelligence Score |
|---|---|---|
| `kimi-k3` | Kimi K3 | 60 |
| `glm-5.3` | GLM-5.3 | 60 |
| `qwen-3.8` | Qwen 3.8 | 58 |
| `inkling` | Inkling | 42 |
| `nemotron-3-ultra` | Nemotron 3 Ultra | 38 |

Intelligence scores are published by [Artificial Analysis](https://artificialanalysis.ai)
and reproduced as catalogue metadata. They are not Coral benchmarks and are not
measured by Coral.

---

## Architecture

```
                 Customer application
                          │
                 Australian API  (/v1, OpenAI-compatible)
                          │
                 Authentication   src/lib/auth
                          │
                 Model registry   src/lib/registry
                          │
                 Routing layer    resolveModel()  ── one AU deployment, no fallback
                          │
                 Compute adapter  src/lib/adapters
                          │
                 Australian compute infrastructure
                          │
                 Open model weights (stored in AU)
```

The public API is never coupled to a GPU provider. Swapping Firmus for Sharon AI,
Amaze AI or NaviGate is configuration plus, at most, a new adapter.

### Key modules

| Path | Responsibility |
|---|---|
| `src/lib/sovereignty.ts` | The only place that decides what may be called Australian sovereign |
| `src/lib/registry/catalogue.ts` | The five models. Product metadata only |
| `src/lib/registry/deployments.ts` | Env-driven deployments **and the offshore gate** |
| `src/lib/registry/index.ts` | Customer-facing model view + `resolveModel()` |
| `src/lib/adapters/` | Compute provider adapters (`openai-compatible`, `development-mock`) |
| `src/lib/auth/apiKeys.ts` | API key generation and verification |
| `src/lib/usage.ts` | Usage metering. Operational metadata only, never content |
| `src/lib/db/schema.ts` | Organisation, API key, model, deployment, usage event |
| `src/app/v1/` | The public API routes |

---

## Running it locally

```bash
npm install
cp .env.example .env.local     # ships with development mocks enabled
npm run db:migrate
npm run db:seed
npx tsx scripts/create-api-key.ts --org "Your Company Pty Ltd" --name "dev"
npm run dev
```

The key is printed once. Then:

```bash
curl http://localhost:3000/v1/models -H "Authorization: Bearer coral_sk_..."
```

Out of the box every model is served by a **development mock**: no GPU, no
weights, no sovereignty claim. Mocks label themselves in the response body, in
the `x-coral-development-mock` header, and in the registry.

---

## The sovereignty controls

1. **Australian-only routing.** A deployment is registered as routable only if
   it declares `INFERENCE_COUNTRY=AU` and `WEIGHT_COUNTRY=AU`. Anything else is
   marked `misconfigured` and can never receive traffic.
2. **No fallback path exists.** `resolveModel()` returns exactly one deployment
   or an error. No adapter knows about a second backend.
3. **Verified means verified.** `australian_sovereign: true` requires a recorded
   verification — who checked, when, and how. Presence in the catalogue proves
   nothing.
4. **Mocks are never sovereign,** whatever their configuration claims, and are
   refused in production unless explicitly re-enabled.
5. **Per-request evidence.** Responses carry `x-coral-deployment`,
   `x-coral-inference-country`, `x-coral-inference-region` and
   `x-coral-sovereignty`.

Audit the current posture at any time:

```bash
npm run sovereignty:check
```

Gate a production deploy on it — this exits non-zero unless all five models are
verified Australian deployments:

```bash
npm run sovereignty:check -- --strict
```

---

## Privacy

Customer prompts and model responses are **never logged or stored**. There is no
column for message content anywhere in the schema, and no code path that writes
it. Usage events record only operational metadata: request id, organisation,
model, deployment, token counts, latency, status.

Streamed responses are metered by reading the `usage` object on the final SSE
chunk — the content deltas are passed through untouched.

---

## Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Development server |
| `npm run build` / `npm start` | Production build and serve |
| `npm run typecheck` | TypeScript |
| `npm run lint` | ESLint |
| `npm test` | Vitest |
| `npm run db:migrate` | Apply migrations |
| `npm run db:seed` | Sync the registry into the database |
| `npm run sovereignty:check` | Audit sovereignty posture |
| `npx tsx scripts/create-api-key.ts --org "..." --name "..."` | Issue an API key |

---

## Connecting real Australian infrastructure

See `DEPLOYMENT.md` for the full procedure. In short: stand up an
OpenAI-compatible server (vLLM or similar) on an Australian GPU with weights on
Australian storage, fill in that model's `CORAL_DEPLOYMENT_*` block, remove
`ADAPTER=development-mock`, verify residency, then record the verification.

Until that is done, this repository serves development mocks and says so.
