# Open Inference

Australian AI compute data first: which open and closed models really run in Australia, what GPUs cost here in AUD, and what every open model costs to run here. Serving comes later.

**Start here:** [docs/one-pager.md](docs/one-pager.md), Caesey's plan in his own words (4 Nov 2026).

## Layout
| Folder | What |
|---|---|
| `docs/one-pager.md` | The current plan. Wins over everything else. |
| `docs/plan-notes.md` | Working notes it came from (question bank, vision map). |
| `docs/buyers.md` | Who might pay, plus the contact log. |
| `docs/research/` | Dated market snapshots. They go stale, so compare instead of trusting old ones. |
| `docs/history/` | Earlier rounds: the Aug 2026 Open Inference notes and the full open-weights dossier (Jul–Oct 2026). |
| `legacy/` | Old builds brought in for reference: Coral (Sep 2026 MVP) and the Australian endpoints prototype (Sep 2026, mock-only). |
| `data/` | Raw daily pulls (dated). |
| `reports/` | What gets published. |

## Daily report (first move 1, built 2026-11-04)
- **Read it:** `reports/latest.md` (one file per day in `reports/`, the full data in `data/<date>/snapshot.json`).
- **Runs itself:** at 6pm Brisbane and at login (launchd job `com.openinference.daily`, which catches up after the Mac was off). It runs the tests, builds the report and commits it locally. Log: `bin/daily.log`.
- **Run by hand:** `bin/daily.sh`, or `python3 -m tracker --offline` to rebuild from today's saved pages.
- **Providers read:** SCX (regions per model), AWS Bedrock Sydney/Melbourne (regions per model), ResetData and Xinference (their own claim that serving is in Australia). Azure, Google, Amaze, Micron21, NorthStar, Datacom and Sovereign Australia AI are listed as not checked yet, with reasons.
- **Scores:** Artificial Analysis. Without a key it uses the saved copy in `data/scores/` (currently 23 Oct). For live scores, put a free `ARTIFICIAL_ANALYSIS_API_KEY=...` in `.env` (gitignored).
- **Code:** `tracker/` (`providers.py` holds parsers and provider facts, `names.py` model-name matching, `build.py`, `report.py`). Tests: `python3 -m unittest discover -s tests`.
- **Turn it off:** `launchctl bootout gui/$(id -u)/com.openinference.daily && rm ~/Library/LaunchAgents/com.openinference.daily.plist`

## First moves (from the one-pager)
1. Automate the daily report across every Australian provider.
2. Collect GPU prices, online and by talking to providers.
3. Work out what every model costs to run here.
4. Rebuild the private model hosting product.
5. Put the data out publicly and start talking to people.
