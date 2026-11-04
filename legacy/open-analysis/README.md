# Open Analysis

Australian AI model data: what models cost in AUD, how fast they are from Australia,
and what Australians use. Built on Artificial Analysis, Vercel and OpenRouter data.

## The 10 data points
1 Price in AUD, 2 Speed from Australia, 3 Spend in Australia, 4 What Australians use,
5 Latency from Australia, 6 Cost per task in AUD, 7 Smartest open model,
8 Value for money in AUD, 9 Open vs closed usage, 10 Providers serving it in Australia
(+ bonus: can it run in Australia)

## Rules
- Don't invent numbers. If a source doesn't have it, leave it empty and say so.
- Label anything global as global.
- Cost per task means Artificial Analysis's cost per Intelligence Index task.
- reference/ holds hand-checked snapshots. Output should match them.
- Keys live in .env, never in code.

## Later
The daily snapshot will feed a separate Model Router project. Keep the output shape stable.

---

## Run

```bash
python3 -m openanalysis
```

Python 3.9+, no dependencies. Keys go in `.env` (see `.env.example`). Output:

| File | What |
| --- | --- |
| `data/snapshots/YYYY-MM-DD.json` | The full snapshot |
| `data/snapshots/YYYY-MM-DD.csv` | One row per model |
| `data/latest.json` | Copy of the most recent snapshot |
| `data/raw/YYYY-MM-DD/` | Raw source responses (gitignored) |

Options: `--from-raw data/raw/2026-10-11` rebuilds a snapshot offline from saved responses,
`--skip-endpoints` skips the per-model provider calls, `--date` sets the snapshot date.

## Check against the references

```bash
python3 -m openanalysis.check
```

For each file in `reference/` this runs the spread-map method on the reference's own figures, then
compares the snapshot of the same date with the reference. A value the snapshot leaves empty is
reported as `empty`, never as a pass. Exit code 1 on any mismatch.

A reference is two files: the hand-checked notes as written (`2026-10-11-spread-map.md`) and the same
figures as data with the expected results (`2026-10-11.json`).

Tests: `python3 -m unittest discover -s tests`

## Sources

| Source | Endpoint | Key | Used for |
| --- | --- | --- | --- |
| Artificial Analysis | `/api/v2/data/llms/models` | `ARTIFICIAL_ANALYSIS_API_KEY` | Intelligence Index |
| Artificial Analysis (beta) | `/api/v2/language/models/free` | same key | Cost per Intelligence Index task |
| Vercel AI Gateway | `/v1/models`, `/v1/models/{id}/endpoints` | none | Prices, providers |
| OpenRouter | `/api/v1/models`, `/api/v1/models/{id}/endpoints` | `OPENROUTER_API_KEY` | Prices, providers, discounts, open-weights status |
| OpenRouter | `/api/v1/providers` | same key | Each provider's headquarters and datacenter countries |
| Reserve Bank of Australia | F11.1 exchange rates CSV, RSS fallback | none | AUD/USD |

**Attribution is required** wherever Artificial Analysis data is shown: credit
[artificialanalysis.ai](https://artificialanalysis.ai/). Every snapshot carries an `attribution` block.

## Where each data point stands

Every value has a `scope`: `global` (a worldwide figure shown in AUD) or `australia` (measured in or
about Australia). Everything filled so far is `global`, except point 10, which lists Australian deployments as
the gateways report them. Nothing is yet measured from Australia.

| # | Field | Status | Definition |
| --- | --- | --- | --- |
| 1 | `price_aud` | filled | List price in AUD per 1M tokens: input, output, 3:1 blend. Ex GST. `cheapest_available` alongside is the lowest price actually charged by any provider on either gateway, with its source. |
| 2 | `speed_from_australia` | planned | |
| 3 | `spend_in_australia` | planned | |
| 4 | `australian_usage` | planned | |
| 5 | `latency_from_australia` | planned | |
| 6 | `cost_per_task_aud` | filled | Artificial Analysis's cost per Intelligence Index task, from its beta API (`artificial_analysis_intelligence_index_cost.cost_per_task.total_cost`). Empty where Artificial Analysis has no figure. |
| 7 | `smartest_open` | filled | Intelligence Index, open-weights flag, rank among open models. |
| 8 | `value_aud` | filled | Intelligence Index points per A$1 of blended token price, for models scoring 30 or more. |
| 9 | `open_vs_closed_usage` | planned | |
| 10 | `providers_in_australia` | filled | Deployments in Australia as the gateways list them: Vercel AI Gateway deployments in an Australian cloud region, at that region's price, and OpenRouter providers that list an Australian datacenter. AUD, ex GST, with `vs_list_price` (the premium over list price). `count: 0` means neither gateway lists one, not that the model can't be had in Australia. |
| + | `runs_in_australia` | planned | |

## Cost per task: the hand-transcribed fallback

Cost per task comes from Artificial Analysis's beta API, and each value says so
(`"source": "artificial_analysis_api"`). The endpoint is beta, so there is a fallback: figures read off
Artificial Analysis's chart by hand into `inputs/cost_per_task/YYYY-MM-DD.csv`.

```
artificial_analysis_slug,chart_label,cost_per_task_usd,note
mimo-v2-6-pro,MiMo-V2.6-Pro,0.13,
```

A hand figure is used only where the API has none, and is labelled `"source": "hand-transcribed"`. Where
both exist the API's is used, and a warning is raised if they differ by more than rounding. Each figure
belongs to one Artificial Analysis entry (a model at one reasoning setting), named by its slug.

## The spread map

Cost against intelligence. Scores are stored with the API's decimals; models are compared in whole
points, as Artificial Analysis's chart displays them, so 46.3 and 46.4 count as the same intelligence.

- **Dominance** – A dominates B when A is at least as smart and no dearer, and better on one of the two.
- **Frontier** – models nothing dominates.
- **Cheapest per intelligence level** – the cheapest model scoring at or above each level.

Each is worked out four ways: `all_models`, `available_models` (listed on Vercel or OpenRouter),
`open_models` and `australian_hosted_models` (deployed in Australia, point 10).

`spread_map.by_cost_per_task` is the main map and the one the references use. It covers every model
Artificial Analysis has a cost for, which is more than its chart shows, so its frontier can include
models the chart leaves out. The reference check compares like with like: the chart's models only. `spread_map.by_token_price` is a secondary view on list price per 1M
tokens. It is a different measure and gives different answers: token price ignores how many tokens a
model spends on a task.

## Things to know

- **List price** is Vercel AI Gateway's model price. For a model not on Vercel it is OpenRouter's price with
  any discount removed (OpenRouter shows prices after discounts it has negotiated), and for a model on
  neither, Artificial Analysis's. For an open-weights model sold by many providers there is no single list
  price; the gateway's default provider stands in for it.
- **Cheapest available** counts full-precision deployments only: FP8 or better, or no quantization stated
  (nearly every closed model states none). The cheapest quantized deployment (fp4, int4 and the like) is
  reported separately as `cheapest_quantized`, with its quantization. Both leave out OpenRouter's `flex`
  endpoints (a slower service tier) and endpoints that are down.
- **`providers_global`** lists every provider on both gateways with its price. On Vercel each provider also
  carries its cloud regions (`regions`, with any region-specific price); on OpenRouter, the provider's
  headquarters and datacenter countries.
- **Providers in Australia** (point 10) come from those two fields. Vercel's region is per deployment, so it is
  the stronger evidence. OpenRouter's datacenter list is per provider and does not say which datacenter serves a
  request, so each entry says which kind it is (`basis`). The spread map has an `australian_hosted_models` view
  using the same global costs; the Australian deployment can cost more (`vs_list_price`).
- **AUD conversion** uses the latest RBA 4pm rate on or before the snapshot date; `fx.rate_date` says which day.
- **Rows** – one per model on either gateway, plus one for each model only Artificial Analysis lists
  (`id` starts `aa:`, `on_gateways` is false).
- **Intelligence Index** – Artificial Analysis lists each reasoning setting as its own entry. A model is
  represented by its best-scoring setting, as on Artificial Analysis's charts.
- **Open weights** means OpenRouter lists a Hugging Face weights repo. Models not on OpenRouter are `null` (unknown).
- **Model matching** – each source names models differently, so they are joined on a normalised name
  (`openanalysis/match.py`). Each snapshot's `report` lists what to review: scores that differ from
  OpenRouter's copy, loose matches, possible duplicates, and large price gaps between the gateways.
  Corrections go in `config/overrides.json`, each with its evidence.

## Schedule

**GitHub Actions** runs the job daily at 08:00 UTC (6pm Brisbane, after the RBA publishes its 4pm rate):
`.github/workflows/daily-snapshot.yml`. It runs the tests, builds the snapshot, checks it against
`reference/`, and commits `data/snapshots/` and `data/latest.json`. A failed run commits nothing and
GitHub emails the repo owner. It can also be started by hand from the Actions tab ("Run workflow").

It needs two repository secrets (Settings → Secrets and variables → Actions):
`ARTIFICIAL_ANALYSIS_API_KEY` and `OPENROUTER_API_KEY`. Without both, the run fails instead of
committing fallback data.

**Mac backup**, to be removed once the Action has run cleanly twice: a launch agent
(`~/Library/LaunchAgents/com.openanalysis.daily.plist`, copy in `deploy/`) runs the same job at 6pm and
writes to `backup/` (gitignored) so it never touches the committed snapshots. Its log is
`~/Library/Logs/open-analysis/daily.log`. If the Mac is asleep at 6pm it runs on next wake; if shut down
or logged out, that day is skipped.

Remove the backup: `launchctl bootout gui/$(id -u)/com.openanalysis.daily && rm ~/Library/LaunchAgents/com.openanalysis.daily.plist`
