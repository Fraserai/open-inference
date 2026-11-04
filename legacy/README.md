# Legacy builds (reference only)

Copied in on 2026-11-04. The originals are untouched in their old folders. Don't build on these without asking Caesey.

## coral/ (Sep 2026)
- **What:** "Australian Sovereign Open Weights Model API": the MVP built on 2026-09-03, the day he named it Coral AI. Next.js 15, TypeScript, Drizzle/SQLite, a model registry, API keys (`coral_sk_` prefix), OpenAI-style `/v1/models`.
- **Status:** prototype. No live inference, no GPUs, no customers. On 2026-09-06 he cancelled the Australian GPU layer.
- **Original:** `~/Desktop/CODEBASES/CORAL`. Its own git history (3 commits) is in `coral/GIT_HISTORY.txt`, and the original repo also has a GitHub remote (`Fraserai/coral`).
- **Left out on purpose:** `.env.local` (secrets), `node_modules`, `.next`, `.git`, and the local `data/coral.db`. Rebuild with `npm install`, then use the drizzle scripts.

## australian-endpoints/ (Sep 2026, Codex)
- **What:** "an Australian equivalent of Hugging Face Inference Endpoints", built in Codex on 2026-09-13 under a strict rule: don't deploy, and mark what is mocked. FastAPI-style Python app with a mock provider, an AWS adapter, a small web UI and tests.
- **Status:** mock only. No paid resources were used. 17 tests passed at the time; they haven't been re-run here.
- **Original:** `~/Documents/Codex/2026-09-13/ai/outputs/australian-endpoints`, plus `work/` (a catalogue update script and two Hugging Face model listings).
- **Left out on purpose:** `state/` (a local admin token and the mock database), `venv`, caches, and `egg-info`.

## open-analysis/ (Oct 2026): the daily data job, trimmed
- **What:** a small Python job with no dependencies (35 tests pass, re-run 2026-11-04). It pulls Artificial Analysis, OpenRouter, Vercel AI Gateway and RBA exchange rates, and writes a dated snapshot of every model.
- **Kept, because Open Inference needs it (first moves 1 and 3):**
  - `sources.py`: fetches models, providers and their datacenter countries.
  - `match.py`: joins models across sources by name. `config/overrides.json` holds the corrections.
  - `fx.py`: RBA AUD rates.
  - `providers_in_australia` (point 10): which models the gateways list as deployed in Australia, plus `vs_list_price`, the **Australian markup**.
  - `smartest_open` (point 7): Intelligence Index, open-weights flag, and rank among open models.
  - `price_aud` (point 1): list price in AUD, the global baseline for the markup.
  - `data/snapshots/`: 4 real snapshots (11, 13, 14 and 23 Oct 2026), a baseline for "the gap hasn't moved".
- **Router-oriented, ignore for now:** the spread map (`metrics.py`, dominance and "cheapest per intelligence level"), `value_aud`, `cost_per_task_aud` and `inputs/cost_per_task`. They're still inside `snapshot.py`, `check.py` and `reference/`, because removing them would break the code and its tests.
- **Left out:** the Astro website (`site/`, `site.py`), the GitHub Actions workflow, the Mac launch agent, `data/raw`, `.env` (real keys) and the CSV copies of the snapshots.
- **Keys it needs to run live:** `ARTIFICIAL_ANALYSIS_API_KEY` and `OPENROUTER_API_KEY` (both free tiers). See `.env.example`.
- **Original:** `~/Desktop/CODEBASES/OPEN-ANALYSIS` (git history in `GIT_HISTORY.txt`).

## Secret scan (gitleaks, 2026-11-04)
2 hits, both false positives: a placeholder `coral_…` key in Coral's README curl example, and the Hugging Face model name "SkinTokens" in `work/qwen-small.json`.
