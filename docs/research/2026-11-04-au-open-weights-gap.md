# Australian open-weights serving gap: snapshot 2026-11-04
_Research Caesey did with claude.ai on 2026-11-04, pasted into Claude Code the same day. Condensed. Every number is `[AI research 2026-11-04]` unless labelled otherwise. It will go stale, so compare against later snapshots rather than trusting it._

## What he said `[Caesey 2026-11-04]`
- "So I spent a few months diving into all this, I found this gap on my own research, left this work for another few months and nothing changed 💀"
- On being told again to go ask buyers: "Again same thing [it] told me 3 months ago".
- "Rent some GPUs, sell inference, make lots of money. Patel said this", after a new Dylan Patel keynote at Modal's Runtime conference.

## Rankings vs Australian hosting `[AI research 2026-11-04]`
- **Artificial Analysis (Intelligence Index v5):** 34 open-weight entries, 27 unique models. Open-weights high is 32 and the overall high is 59.
- **Only one ranked open model runs on Australian compute** at SCX or ResetData: MiniMax-M3 (19). The other 26 don't.
  - Offshore at SCX: DeepSeek V4.1 Flash 1017 (32), GLM-5.3 (32) and GLM-5.3-Flash (28).
- **SCX still lists 12 Australian models:**
  - 6 open chat models: Qwen3-32B, Gemma 4 31B, Llama 4 Maverick, MiniMax-M2.7, MiniMax-M3, gpt-oss-120b
  - 4 of its own: coder, MAGPiE, scx-stt, Apex
  - 2 open non-chat: E5-Mistral embeddings, Whisper
- **SCX routing:** one base URL with no documented way to lock a request to Australia. MiniMax-M3 is listed for both the US and Australia.
- **ResetData's docs** list 4 chat models (GLM-5.2, Gemma 4 26B, Qwen3 Coder 30B, Llama 3.1 8B), none with a current AA score. The full catalogue needs a login.
- **Xinference** advertises Kimi K3 and DeepSeek V4.1 Flash on Australian GPUs (build unclear), with GLM 5.3 on request.
- **Amaze** lists 34 open models, with its catalogue marked "coming soon".
- **The top 8 open models are all Chinese.** No ranked US or European open model is hosted in Australia.
- **Kimi K3.1 Pro (46)** isn't in the index yet because its weights weren't out. If it lands and gets hosted locally, the open vs closed gap shrinks to 13.
- **Two gaps:**
  - Hosting gap: 13 points (top open model at 32 vs the best Australian-hosted at 19).
  - Open vs closed gap: 27 points (32 vs 59).
- **Not covered:** hyperscalers (AWS Sydney etc.) weren't checked. "Hosted in Australia" also isn't the same as sovereign (SCX sits in a US-owned Equinix site).

## Inference economics: Dylan Patel, Modal Runtime keynote `[AI research 2026-11-04]` (talk not watched; summaries only)
- One megawatt of B300s serving DeepSeek V4.1 Flash at 60% utilisation earns about $70M a year. B300s at $6 per hour are worth signing up for to sell tokens.
- **Claude's margin stress test,** using the slide's revenue per GPU-hour:

| GPU rent per hour | GLM 5.3 margin | Kimi K3 margin (after a 30% fee) |
|---|---|---|
| $4.50 | 68% | 35% |
| $6.00 | 57% | 23% |
| $8.21 (public median) | 41% | 6% |

- Public on-demand B300s cost $7.10 to $17.80 an hour. The slide's $14M per MW assumes a five-year contract. More than 100 companies already sell tokens, and rents are rising.
- The Kimi K3 licence needs a separate deal only above $20M in revenue.
- Smallest real test: one 8-GPU node at $6 an hour, about US$420k a year.

## Compared with his Aug–Oct 2026 research (from memory)
- **SCX's ~12 Australian models: unchanged.** He found the same list on 2026-09-02 and judged it "all old and shit compared to today's top 10" `chatgpt:6a98133d-d26c-83ec-be90-2f8e27378d5d`. govai.gov.au also listed 12 on 2026-09-03 `chatgpt:6a98e34b-73bc-83ec-9b6c-edfb2d2614e2`.
- **Amaze's 34-model listing is not new.** A 34-model listing was already in his 2026-09-02 research, so it isn't evidence that providers have started moving.
- **Xinference was already on his radar** in 5 chats between 2026-09-01 and 10-07. Whether its Kimi K3 and DeepSeek V4.1 Flash listings are new hasn't been checked.
- **GPU price then:** Amaze B300 at about A$8,431.50 per GPU per month including GST (2026-08-30), roughly A$11.50 an hour, which is about the same as today's public median. `[AI research 2026-08-30]` `chatgpt:6a917e1c-6dc0-83ec-869a-83c3b70e44ed`
- **The buyer question was raised before.** On 2026-08-29 Claude said distribution to buyers was the scarce part, and he said he had no warm buyers `claude:33ac6ae4-c4bc-4622-84fe-44ca2fb23a04`. No later chat shows a customer conversation.
- **Throughput was never measured.** Both the August break-even maths (about 6.2B tokens a month for Inkling-Small) and today's margin table assume a tokens-per-GPU figure nobody has tested.
- **His 2026-09-06 decision (D-052):** cancel the Australian GPU layer "until we have a real business that makes money" `chatgpt:6a98e34b-73bc-83ec-9b6c-edfb2d2614e2`.

## SemiAnalysis slides (Patel keynote, Modal Runtime), photographed by Caesey 2026-11-04
_Read off his photos of the slides. The source is SemiAnalysis "Anatomy of an Inference Endpoint (draft)" and the AI Cloud TCO Model. The economics are US-based, not Australian._
- **What SemiAnalysis builds** (slide dated 2026-09-30):
  - 14 institutional models (Tokenomics, AI Cloud TCO, Datacenter etc.)
  - Benchmarks: InferenceX, AgentX, EndpointX (first edition coming), SandboX (upcoming)
  - Ratings: ClusterMAX 3.0, with 323 providers tracked, 77 reviewed and 19 Medallions
  - Data: hourly GPU spot/contract composite indexes, a free H100 1-year contract index since Apr 2026, and an H100 composite on Bloomberg (SAH100SC)
- **Cost per MW per year:** $9M to own and run B300s, about $14M on a five-year rental, and $70M+ from selling open-source tokens. Serving GLM 5.3 or Kimi K3 on GB300 with stock vLLM or SGLang gives a 70%+ gross margin.
- **Per B300 GPU-hour, at a GPU rental of $4.50:**

| | Kimi K3 | GLM 5.3 |
|---|---|---|
| Revenue | $12.80 | $13.92 |
| Licensing fee | Moonshot $3.84 (30%) | none |
| Token-provider gross profit | $4.46 (35%) | $9.42 (68%) |
| Neocloud profit | $2.07 | $2.07 |
| Neocloud cost | $2.43 | $2.43 |

  The neocloud cost breaks down as server $1.48, colocation $0.39, networking $0.26, electricity $0.18, other cluster $0.09 and other operating $0.03.
- **What it means `[summary]`:** most of the value goes to whoever sells the tokens, not whoever rents out the GPUs (GLM: $9.42 an hour vs $2.07). Australian B300 rent of about A$11.50 an hour (Amaze, Aug) is well above the $4.50 assumed here.
- **Relevance:** SemiAnalysis's coming EndpointX benchmark and its ClusterMAX ratings overlap with an "Australian AI data" business, so they're a possible competitor or reference point.
