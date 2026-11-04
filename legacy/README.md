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

## Secret scan (gitleaks, 2026-11-04)
2 hits, both false positives: a placeholder `coral_…` key in Coral's README curl example, and the Hugging Face model name "SkinTokens" in `work/qwen-small.json`.
