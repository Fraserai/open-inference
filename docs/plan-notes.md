# Open Inference: the plan (v2, 2026-11-04)
> **Replaced by his own version:** [open-inference-one-pager](one-pager.md) `[Caesey 2026-11-04]`. Kept below as the working notes it came from; where they differ, the one-pager wins.
_Drafted with Claude Code on 2026-11-04. Lines marked `[Caesey]` are his decisions; everything else is `[AI suggestion]` until he confirms it. Background: [topics/open-weights](history/open-weights-dossier.md), [research/2026-11-04-au-open-weights-gap](research/2026-11-04-au-open-weights-gap.md), [buyers](buyers.md)._

## Decided `[Caesey 2026-11-04]`
- Revive **Open Inference**, starting solo on the **data side** (the SemiAnalysis way).
- **Step 1:** track and record every top open model, every Australian AI/GPU provider, and the list of models **not** hosted in Australia.
- **Step 2:** work out in depth what each model would cost to run on Australian GPU providers.
- **Step 3:** create the data and put it out publicly.
- **Outreach comes after** there's something to show.

## Draft lines `[AI suggestion 2026-11-04]`
- **What:** the top open AI models, served in Australia, processed in Australia.
- **Who for:** Australian companies that can't send data overseas. Health, legal and finance first.
- **The line:** stored in Australia isn't processed in Australia.
- **Rules:**
  - Nothing leaves Australia except the model weights coming in.
  - No GPU commitments until a customer is paying.
  - One step at a time.
- **Later steps:**
  - Show the data to the companies already shopping (see buyers.md).
  - First customer gets a managed endpoint on hourly-rented Australian GPUs.
  - Moonshot: shared per-token serving of every top open model on one Australian API.
- **Scoreboard:**
  - Index live
  - First 10 people have seen it
  - First "I need this model here"
  - First paying customer
  - First A$10k/month

## Data to build in Step 1–2 (working list)
- **Models:** every top open model with its Artificial Analysis score, licence, size, GPUs needed (BF16/FP8/INT4) and maker's country.
- **Providers:** every Australian inference or GPU provider, with ownership, data centre location, certifications (IRAP/HCF), region lock (yes/no/unclear) and how to buy (API, on-demand, contract).
- **Availability:** a model × provider grid showing whether each model is served onshore, served offshore, or not offered.
- **GPU prices (AUD):** per GPU-hour and per month, by provider and GPU type, dated.
- **Cost to run:** per model per provider, the monthly floor, cost per million tokens at assumed utilisation, and break-even volume. Throughput comes from public benchmarks (e.g. SemiAnalysis InferenceX) until measured.

## Vision map v2 (riff, 2026-11-04)
_The lines marked `[Caesey 2026-11-04]` are his calls. The structure is `[AI suggestion]`, modelled on SemiAnalysis's product lines and adapted to AU/NZ._
- **His calls `[Caesey 2026-11-04]`:**
  - Drop the "does it know Australia" model benchmark.
  - Take SemiAnalysis's playbook and apply it to Australian GPU providers and neoclouds.
  - Add an always-updated map of ALL models served in Australia, closed and open.
  - He wants to go deep on compute, power, serving and data intelligence.
- **Data:**
  - AU Model Map: every closed and open model served in Australia, by provider, onshore vs offshore. Daily.
  - Missing Top 10, weekly.
  - Release lag: days from a model's global launch until it's served in Australia.
  - AU GPU Price Index in AUD.
  - Sovereignty premium: AU token prices vs global prices for the same model.
- **Ratings & benchmarks:**
  - "ClusterMAX for Australia": rate Australian GPU providers and neoclouds (ownership, certifications, region lock, availability, price, support).
  - AU endpoint benchmark: speed, time to first token and uptime of Australian-served endpoints, measured from AU/NZ cities.
- **Models (spreadsheets clients buy):**
  - AU cost to serve every open model on every Australian provider.
  - AU Cloud TCO in AUD.
  - AU datacenter + power model: capacity announced vs live, and electricity cost by state.
- **Research:** a monthly "State of AI compute in Australia" report plus a weekly newsletter.
- **Serving (long term):** managed endpoints first, then rented GPUs serving the missing models onshore. One API is optional. NZ after Australia.

## Tagline candidates (2026-11-04, undecided)
- "All of it. In Australia. In our currency." (from his own words `[Caesey 2026-11-04]`)
- "Global open weights. Australian compute. Australian company. Australian customers." `[Caesey 2026-08-28]`
- Claude's options: "Know what runs here. Then run it here." / "Australia's AI compute, measured." / "Global models. Australian compute. Real numbers."
- Rejected: "the source of truth for running open AI models in Australia and NZ…" `[Caesey 2026-11-04]` ("probs dont like this line")

## Question bank for the empty page (2026-11-04)
_What he wants to know and share, all in AUD `[Caesey 2026-11-04]` ("i wanna know it all and share it… in our currency all of it"). The questions were drafted by Claude._
- **Chips:** what does a GB300 / B300 / H200 cost in AUD, landed in Australia? Who sells them here, and how long is the wait?
- **GPU rental:** who rents GPUs in Australia, at what AUD rate per hour and per month, on-demand vs contract? Who has stock now?
- **Data centres:** what does an AI data centre cost to build in Australia per MW? Who's building (AirTrunk, NextDC, CDC, Firmus, ResetData), where, how big, and when? Announced vs live?
- **Power:** what does a MW cost per year by state? How much of a token's cost is electricity? Where's the cheapest place to run AI?
- **Models:** which closed and open models are actually processed in Australia, and by whom? What's missing, and how far behind is Australia?
- **Tokenomics:** what does a million tokens cost to serve here vs what's charged? Who takes the margin (chips, data centres, neoclouds, token sellers)?
- **Market:** who buys AI compute in Australia, and what are the rules (APRA, Privacy Act, government)?
