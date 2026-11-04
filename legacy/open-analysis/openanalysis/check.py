"""Check the job's output against the hand-checked snapshots in reference/.

    python3 -m openanalysis.check

Each reference is checked twice. First the spread-map calculation is run on the
reference's own figures, which tests the method. Then the snapshot for the same
date is compared with the reference, which tests the data. A value the snapshot
leaves empty is reported as empty, not as a pass.
"""

import json
import sys

from . import config, metrics

OK, MISMATCH, EMPTY = "ok", "MISMATCH", "empty"
REFERENCE_DIR = config.ROOT / "reference"


def _tally(results, label, pairs):
    """pairs: [(what, expected, actual)]. One line when all agree, one per difference otherwise."""
    wrong = [(what, expected, actual) for what, expected, actual in pairs if expected != actual]
    if pairs and not wrong:
        results.append((OK, f"{label}: {len(pairs)} of {len(pairs)} agree"))
    for what, expected, actual in wrong:
        results.append((MISMATCH, f"{label}: {what}: reference says {expected}, got {actual}"))


def _compare_spread(results, label, expected, points):
    summary, per_model = metrics.spread_map(points)
    counts = [k for k in ("models", "dominated", "dominance_relationships", "same_intelligence_relationships")
              if k in expected]
    _tally(results, f"{label} counts ({', '.join(f'{expected[k]} {k}' for k in counts)})",
           [(k, expected[k], summary[k]) for k in counts])
    if "frontier" in expected:
        _tally(results, f"{label} frontier", [("models", expected["frontier"], [p["id"] for p in summary["frontier"]])])
    _tally(results, f"{label} cheapest model per intelligence level",
           [(f">={level}", slug, metrics.cheapest_at_least(summary, int(level)))
            for level, slug in expected.get("cheapest_at_least", {}).items()])
    _tally(results, f"{label} best alternative for each dominated model",
           [(slug, swap, per_model.get(slug, {}).get("dominated_by")) for slug, swap in expected.get("dominated_by", {}).items()])
    _tally(results, f"{label} number of models each one dominates",
           [(slug, count, per_model.get(slug, {}).get("dominates_count"))
            for slug, count in expected.get("dominates_count", {}).items()])


def check_method(reference):
    """Run the spread map on the reference's own intelligence and cost figures."""
    results = []
    costed = [m for m in reference["models"] if m["cost_per_task_usd"] is not None]
    subsets = {
        "all_models": costed,
        "public_models": [m for m in costed if m["public"]],
        "open_models": [m for m in costed if m["open_weights"]],
    }
    for name, expected in reference["expected"].items():
        points = [{"id": m["artificial_analysis_slug"], "cost": m["cost_per_task_usd"], "intelligence": m["intelligence"]}
                  for m in subsets[name]]
        _compare_spread(results, name, expected, points)
    return results


def check_snapshot(reference, snapshot):
    """Compare the snapshot's own values for the reference's models."""
    results = []
    rows = {}
    for model in snapshot["models"]:
        rows.setdefault(model["ids"]["artificial_analysis"], model)

    missing = [m["name"] for m in reference["models"] if m["artificial_analysis_slug"] not in rows]
    for name in missing:
        results.append((MISMATCH, f"model not in snapshot: {name}"))
    present = [(m, rows[m["artificial_analysis_slug"]]) for m in reference["models"]
               if m["artificial_analysis_slug"] in rows]

    # The chart shows whole points and the API one decimal, so agreement means within half a point.
    _tally(results, "intelligence index, within rounding of the chart",
           [(m["name"], True, row["intelligence"] is not None and abs(row["intelligence"]["index"] - m["intelligence"]) <= 0.5)
            for m, row in present])

    for field, row_field, label in (("open_weights", "open_weights", "open or closed weights"),
                                    ("public", "on_gateways", "publicly available (listed on a gateway)")):
        stated = [(m, row) for m, row in present if m[field] is not None]
        unknown = [m["name"] for m, row in stated if row[row_field] is None]
        _tally(results, label, [(m["name"], m[field], row[row_field]) for m, row in stated if row[row_field] is not None])
        if unknown:
            results.append((EMPTY, f"{label}: unknown in snapshot for {', '.join(unknown)}"))

    costed = [(m, row) for m, row in present if m["cost_per_task_usd"] is not None]
    have_cost = [(m, row) for m, row in costed if row["cost_per_task_aud"]]
    # The chart shows cents; the snapshot keeps the source's precision.
    _tally(results, "cost per task, USD, within rounding of the chart",
           [(m["name"], True, abs(round(row["cost_per_task_aud"]["usd"] + 1e-9, 2) - m["cost_per_task_usd"]) <= 0.0051)
            for m, row in have_cost])
    by_source = {}
    for _, row in have_cost:
        by_source[row["cost_per_task_aud"]["source"]] = by_source.get(row["cost_per_task_aud"]["source"], 0) + 1
    if by_source:
        results.append((OK, f"cost per task source: {by_source}"))
    if len(have_cost) < len(costed):
        reason = snapshot["spread_map"]["by_cost_per_task"].get("reason", "")
        results.append((EMPTY, f"cost per task: empty in snapshot for {len(costed) - len(have_cost)} of {len(costed)} "
                               f"models. {reason}"))

    # The spread map for the reference's models, from the snapshot's own intelligence
    # scores. Cost comes from the snapshot only if it has every one; a currency
    # conversion scales all costs alike, so it does not change which model dominates.
    own_cost = len(have_cost) == len(costed)
    source = "snapshot intelligence and snapshot cost" if own_cost else "snapshot intelligence, reference cost"

    def points(pairs):
        return [{"id": m["artificial_analysis_slug"], "intelligence": metrics.whole_points(row["intelligence"]["index"]),
                 "cost": row["cost_per_task_aud"]["aud"] if own_cost else m["cost_per_task_usd"]}
                for m, row in pairs if row["intelligence"]]

    subsets = {
        "all_models": costed,
        "public_models": [(m, row) for m, row in costed if row["on_gateways"]],
        "open_models": [(m, row) for m, row in costed if row["open_weights"]],
    }
    for name, expected in reference["expected"].items():
        _compare_spread(results, f"spread map ({source}) {name}", expected, points(subsets[name]))
    return results


def main():
    worst = OK
    references = sorted(REFERENCE_DIR.glob("*.json"))
    if not references:
        print(f"No reference files in {REFERENCE_DIR}")
        return 1
    for path in references:
        reference = json.loads(path.read_text())
        print(f"Reference {reference['date']}: {reference['title']}")
        sections = [("A. Method, run on the reference's own figures", check_method(reference))]
        snapshot_path = config.DATA_DIR / "snapshots" / f"{reference['date']}.json"
        if snapshot_path.exists():
            sections.append((f"B. Snapshot {snapshot_path.relative_to(config.ROOT)}",
                             check_snapshot(reference, json.loads(snapshot_path.read_text()))))
        else:
            sections.append((f"B. Snapshot for {reference['date']}", [(EMPTY, "no snapshot for this date")]))
        for title, results in sections:
            print(f"  {title}")
            for state, message in results:
                print(f"    {state:<9}{message}")
                if state == MISMATCH:
                    worst = MISMATCH
    return 1 if worst == MISMATCH else 0


if __name__ == "__main__":
    sys.exit(main())
