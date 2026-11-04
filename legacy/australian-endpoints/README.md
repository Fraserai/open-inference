# Australian Endpoints

Local, mock-backed flow: select a Hugging Face model → select AWS Australia / Sydney → deploy → receive an OpenAI-compatible local endpoint and API key.

**No paid resources have been created. No live inference has been verified.**

## Run locally

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python scripts/run_local.py
```

Open http://127.0.0.1:8787. The launcher binds to loopback and **forces mock mode and disables live deployment**, regardless of environment settings. It makes no AWS calls even if AWS credentials are present. Local visitors use the demo without login. Remote access requires the generated admin token from ignored `state/admin-token`. AWS mode always requires admin authentication.

## What works vs what is mocked

| Surface | Status |
| --- | --- |
| Model selection | Working UI; 14 mock-only models from the supplied Artificial Analysis chart, searchable and in chart order |
| Provider selection | AWS Sydney selectable; Firmus AI, Sharon AI, Navigate Network, Amaze AI and Microsoft Azure Australia listed as planned, disabled integrations |
| Deploy button and progress | Working local API + persistent state machine; cloud operations simulated |
| URL and API key | Real local URL and random endpoint-scoped key; only its hash is stored, plaintext shown once |
| API authentication | Wrong, rotated, deleted or cross-endpoint keys rejected |
| Chat Completions / model listing | OpenAI-compatible local API; response explicitly says it is mocked |
| AWS Sydney adapter | Implemented against documented SageMaker APIs; disabled, not live-validated |
| GPU, model weights, real inference | Not provisioned or verified |

The sandbox returns a canned response. It does not download weights, connect to Hugging Face at runtime, call AWS or invent token usage. A$0 describes this simulation, not a GPU price. On page reload, generate a replacement key; doing so revokes the old one.

## Supplied model shortlist

The picker follows the supplied **Artificial Analysis Intelligence Index v4.3 — Open Source Models** chart, dated **12 September 2026 by its filename**. Scores below are the displayed integers; they are not a live leaderboard fetch or unrounded measurements. Evaluation settings describe the chart run, not a deployed runtime setting.

| Model | Evaluation setting | Displayed score |
| --- | --- | --- |
| GLM-5.3 | max | 45 |
| Kimi K3 | max | 44 |
| GLM-5.3-Flash | Not specified | 42 |
| Qwen3.8 2.4T A95B | Not specified | 40 |
| DeepSeek V4.1 Flash | max | 40 |
| DeepSeek V4 Pro 0813 | max | 36 |
| Qwen3.8 27B | xhigh | 34 |
| K2 Horizon 375B A23B | Not specified | 31 (estimate) |
| MiniMax-M3 | Not specified | 30 |
| Inkling | Not specified | 26 |
| Nemotron 3 Ultra | Not specified | 23 |
| Muse Glimmer | high | 18 |
| Mistral Medium 3.5 | Not specified | 15 |
| gpt-oss-120B | high | 12 |

K2 Horizon's independent evaluation is forthcoming according to the chart legend. All 14 entries are **mock-only**. Their `mock/` identifiers are local catalog keys, not Hugging Face repository names. Repository, licence, revision, runtime compatibility and GPU sizing require verification. The UI does not apply the previous one-L4 configuration to these models. The API rejects their use in live mode before making provider calls.

The two earlier Qwen models are retained only as AWS adapter connection candidates and for old endpoint compatibility; they are not in the new mock picker. They were checked against the Hugging Face Hub on 13 September 2026:


- `Qwen/Qwen3-0.6B`, Apache 2.0, revision `c1899de289a04d12100db370d81485cdf75e47ca`.
- `Qwen/Qwen3-4B`, Apache 2.0, revision `1cfa9a7208912126459214e8b04321603b3df60c`.

These are configuration candidates, not live-validated deployments.

## Local API

Copy the endpoint URL and key from the UI. Set `AU_API_KEY` in your client environment and use the UI's Python example (requires `openai`). Requests and completions are not saved by the application.

- `GET /endpoints/{id}/v1/models`
- `POST /endpoints/{id}/v1/chat/completions` — JSON and SSE streaming.

This is Chat Completions compatibility, not the entire OpenAI API. No billing, accounts, autoscaling or additional provider adapters are included.

## AWS adapter boundary

`app/provider.py` implements create/describe/delete SageMaker operations for Sydney (`ap-southeast-2`), using one `ml.g6.2xlarge` instance, a versioned AWS vLLM container and pinned model revision. Inference uses server-side AWS credentials and SageMaker runtime routing. Clients get application keys, never AWS credentials.

GPU capacity, quota, IAM permissions, container availability, pinned revision loading and real inference still need live acceptance. Both `PROVIDER_MODE=aws` and `ENABLE_DEPLOYMENTS=true` are required for future live operation. Use a different `DATABASE` for live mode; the application rejects mixing mock and real state. The local launcher cannot enable this path. Future live setup requires separate authorisation, AWS access, an execution role, Sydney GPU quota and an HTTPS application server. None is configured here.

Reconciliation persists work before cloud calls and checks deterministic resource names on retries/restarts. Failures request cleanup. Deletion is complete only after absence is confirmed. One active endpoint is allowed. Expiry requests deletion after 60 minutes, but requires this service to be running and AWS responding: **not an independent spending cap**. A GPU incurs charges without inference traffic. Live operation requires monitoring and an independent cleanup strategy.

This is a local, single-workspace prototype. Production hosting, tenant isolation, distributed workers, production rate limiting, billing and a residency audit are outside scope. Use one server worker per database. The gateway runs wherever the application server runs; Sydney compute alone does not establish end-to-end Australian residency.

## Verify

```sh
.venv/bin/pytest
.venv/bin/ruff check app tests scripts
```

Tests use local mock responses and AWS SDK stubs. They do not provision resources.

## Primary references

- [AWS SageMaker OpenAI-compatible endpoints](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints-openai-compatible.html)
- [Hugging Face SageMaker vLLM deployment and invocation](https://huggingface.co/docs/sagemaker/en/tutorials/sagemaker-sdk/deploy-sagemaker-sdk)
- [AWS streaming API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpointWithResponseStream.html)
- [Qwen3 0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), [Qwen3 4B](https://huggingface.co/Qwen/Qwen3-4B)
