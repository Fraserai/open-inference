"""Daily job: python3 -m openanalysis"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, snapshot, sources


def main(argv=None):
    parser = argparse.ArgumentParser(prog="openanalysis", description="Build today's Open Analysis snapshot.")
    parser.add_argument("--date", type=date.fromisoformat, help="Snapshot date (default: today in Sydney)")
    parser.add_argument("--from-raw", type=Path, help="Rebuild from a saved data/raw/<date> folder instead of fetching")
    parser.add_argument("--skip-endpoints", action="store_true", help="Skip the per-model Vercel /endpoints calls")
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = parser.parse_args(argv)

    config.load_env()
    try:
        if args.from_raw:
            raw, status = sources.load_raw(args.from_raw)
            snapshot_date = args.date or date.fromisoformat(args.from_raw.name)
        else:
            snapshot_date = args.date or datetime.now(ZoneInfo(config.TIMEZONE)).date()
            raw, status = sources.collect(skip_endpoints=args.skip_endpoints)
            sources.save_raw(raw, status, args.data_dir / "raw" / snapshot_date.isoformat())

        latest = args.data_dir / "latest.json"
        previous_fx = json.loads(latest.read_text())["fx"] if latest.exists() else None
        cost_per_task = sources.load_cost_per_task(snapshot_date, config.COST_PER_TASK_DIR)
        result = snapshot.build(raw, status, snapshot_date, previous_fx, cost_per_task)
        path = snapshot.write(result, args.data_dir)
    except Exception as error:
        print(f"openanalysis: FAILED: {error}", file=sys.stderr)
        return 1

    summary, rate = result["summary"], result["fx"]
    print(f"Snapshot {result['snapshot_date']} -> {path}")
    print(f"  FX: A$1 = US${rate['aud_usd']} (RBA, {rate['rate_date']}, {rate['method']})")
    print(f"  Models: {summary['models']} | priced: {summary['with_price']} | "
          f"with intelligence: {summary['with_intelligence']} | with cost per task: {summary['with_cost_per_task']} | "
          f"open weights: {summary['open_weights']}")
    for name, state in result["sources"].items():
        print(f"  {name}: {state['status']}" + (f" ({state['detail']})" if state.get("detail") else ""))
    for warning in result["report"]["warnings"]:
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
