# SemiAnalysis playbook + Patel Runtime talk: research 2026-11-04
_Web research by Claude Code, labelled `[AI research 2026-11-04]`. Mostly secondary reporting; SemiAnalysis's financials are unaudited._

## The talk
- **"Compute, capital, and who actually delivers it"**, Dylan Patel (CEO, SemiAnalysis) at Modal's Runtime 2026 in San Francisco on 2026-10-01. The video went up around 2026-11-04. [YouTube](https://www.youtube.com/watch?v=uA5NMUadmgg), [Runtime](https://frontend.modal.com/runtime)
- No transcript or write-up was found online. The slide numbers Caesey photographed are in [2026-11-04-au-open-weights-gap](2026-11-04-au-open-weights-gap.md).

## How SemiAnalysis makes money
- **Started** as a Substack newsletter. It now has 200k+ subscribers; the paid tier is about US$500/yr, but it's a small share of revenue.
- **Revenue:** about US$20M in 2025, projected at US$100M+ in 2026 (The Information, via [AI Weekly](https://aiweekly.co/alerts/semianalysis-core-research-eyes-100m-year-on-buy-side-demand)). About 60 staff.
- **Most money comes from institutional lines:** Core Research, industry models (e.g. AI Cloud TCO, Tokenomics), a data product, and consulting.
- **Buyers:** hedge funds, asset managers, venture investors, corporate strategy teams, hyperscalers, chip companies and startups.
- **Credibility comes from free public goods:**
  - InferenceX (an open benchmark)
  - ClusterMAX ratings (323 providers tracked)
  - A free H100 rental-price index, now on Bloomberg (SAH100SC)
- **Known criticism:** the companies they rate are often their paying clients.

## InferenceX: free throughput data (answers "what does one GPU produce?")
- **What it is:** an open, vendor-neutral benchmark. Code, data and dashboard are open source, and any chart can be exported as CSV. [About](https://inferencex.semianalysis.com/about)
- **Metrics:** tok/s per GPU, tok/s per user, throughput per MW, time to first token, cost per million tokens and joules per token. AgentX covers agentic coding workloads.
- **Hardware:** H100, H200, B200, B300, GB200, GB300, MI300X/325X/355X, TPUv7 and others.
- **Open models:** GLM-5/5.1/5.2, DeepSeek-V4-Pro and V4.1-Flash, Kimi K2.5/K2.6/K3, and more. Which model/chip pairings have results needs checking on the dashboard.
- **Formula:** cost per 1M tokens = GPU cost per hour ÷ (tok/s per GPU × 3600) × 1,000,000. Example: a $4/hr GPU at 1,000 tok/s ≈ $1.11 per 1M tokens.

## What this means for Open Inference `[summary]`
- **Step 2 can be done for free:** take InferenceX throughput (per model and GPU) and divide it into Australian GPU prices in AUD. That gives the cost to serve each top open model in Australia. Nobody publishes this.
- **Free public goods build trust and the audience:** an Australian model-availability index, an AUD GPU price index, and the cost-to-serve table.
- **Paid comes later:** an Australian cost-to-serve model for investors and providers, briefings for enterprises, then serving.
- **Australia is a much smaller buyer pool** than SemiAnalysis's hedge funds. Data is the wedge into serving, not the whole business.
- **Watch the conflict of interest:** if Open Inference later serves models, its ratings of competitors need to be transparent.
