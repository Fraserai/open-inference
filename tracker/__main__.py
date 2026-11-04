"""python3 -m tracker [--date YYYY-MM-DD] [--offline]

Fetches every source, writes data/<date>/snapshot.json and reports/<date>.md, and
copies the report to reports/latest.md. --offline rebuilds from data/raw/<date>/.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import build, report, scores

ROOT = Path(__file__).resolve().parent.parent


def load_env(path):
    """KEY=VALUE lines from a gitignored .env; values never printed."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def previous_snapshot(day):
    days = sorted(p.name for p in (ROOT / "data").iterdir()
                  if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name < day)
    if not days:
        return None
    path = ROOT / "data" / days[-1] / "snapshot.json"
    return json.loads(path.read_text()) if path.exists() else None


def main():
    parser = argparse.ArgumentParser(prog="tracker")
    parser.add_argument("--date", help="snapshot date (default: today in Brisbane)")
    parser.add_argument("--offline", action="store_true", help="rebuild from data/raw/<date>/")
    args = parser.parse_args()
    day = args.date or datetime.now(ZoneInfo("Australia/Brisbane")).date().isoformat()
    load_env(ROOT / ".env")

    pages, fetch_status = build.fetch_all(ROOT / "data" / "raw" / day, offline=args.offline)
    or_models = build._json(pages.get(scores.OPENROUTER_MODELS_URL), "data")
    scores_doc, scores_status = scores.load(day, ROOT / "data" / "scores",
                                            os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY"), or_models, args.offline)
    snapshot = build.build(day, pages, fetch_status, scores_doc, scores_status, previous_snapshot(day))

    out_dir = ROOT / "data" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=1))
    text = report.render(snapshot)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"{day}.md").write_text(text)
    (ROOT / "reports" / "latest.md").write_text(text)

    failed = [p["name"] for p in snapshot["providers"] if p["status"] != "ok"]
    print(f"{day}: {len(snapshot['top_open'])} top open models, {len(snapshot['missing'])} missing; "
          f"scores {snapshot['scores']['status']} ({snapshot['scores']['as_of']})"
          + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    return 1 if len(failed) == len(snapshot["providers"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
