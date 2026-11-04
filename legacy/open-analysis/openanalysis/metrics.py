"""Phase 1 calculations: blended price and the model spread map."""

import math


def blended(input_price, output_price):
    """Artificial Analysis convention: 3 parts input to 1 part output."""
    return (3 * input_price + output_price) / 4


def whole_points(index):
    """Intelligence Index as Artificial Analysis charts display it: whole points.

    Stored scores keep the API's decimals. Only the spread map's comparison uses
    whole points, so 46.3 and 46.4 count as the same intelligence, as they do on
    the chart, rather than one beating the other on a tenth of a point.
    """
    return math.floor(index + 0.5)


def dominates(a, b):
    """a is at least as smart and no dearer than b, and better on one of the two."""
    return (a["cost"] <= b["cost"] and a["intelligence"] >= b["intelligence"]
            and (a["cost"] < b["cost"] or a["intelligence"] > b["intelligence"]))


def spread_map(points, cost_field="cost"):
    """Cost against intelligence for a set of models.

    points: [{"id", "cost", "intelligence"}] with cost > 0. "intelligence" is what models are
    compared on (whole points); an optional "index" is the unrounded score, reported as is.
    Returns (summary, per_model). The summary holds the frontier (models nothing
    dominates) and the cheapest model for every intelligence level; per_model holds
    each model's dominance.
    """
    def entry(point):
        return {"id": point["id"], "intelligence_index": point.get("index", point["intelligence"]),
                cost_field: point["cost"]}

    per_model, relationships, same_intelligence = {}, 0, 0
    for point in points:
        dominators = [other for other in points if dominates(other, point)]
        relationships += len(dominators)
        same_intelligence += sum(1 for d in dominators if d["intelligence"] == point["intelligence"])
        # The swap to suggest: the cheapest model that is at least as smart.
        swap = min(dominators, key=lambda d: (d["cost"], -d["intelligence"], d["id"]), default=None)
        per_model[point["id"]] = {
            "on_frontier": not dominators,
            "dominated_by": swap["id"] if swap else None,
            "dominated_by_count": len(dominators),
            "dominates_count": sum(1 for other in points if dominates(point, other)),
        }

    frontier = sorted((p for p in points if per_model[p["id"]]["on_frontier"]),
                      key=lambda p: (p["cost"], p["intelligence"], p["id"]))

    # Along the frontier each step up in cost buys more intelligence, so each frontier
    # model is the cheapest answer for the levels between the previous model and itself.
    levels, covered = [], -1
    for point in frontier:
        if point["intelligence"] > covered:
            levels.append({"intelligence_from": covered + 1, "intelligence_to": point["intelligence"], **entry(point)})
            covered = point["intelligence"]

    return {
        "models": len(points),
        "dominated": sum(1 for stats in per_model.values() if not stats["on_frontier"]),
        "dominance_relationships": relationships,
        "same_intelligence_relationships": same_intelligence,
        "frontier": [entry(p) for p in frontier],
        "cheapest_per_intelligence_level": levels,
    }, per_model


def cheapest_at_least(summary, intelligence):
    """Id of the cheapest model scoring at or above a level, or None if nothing reaches it."""
    for level in summary["cheapest_per_intelligence_level"]:
        if level["intelligence_from"] <= intelligence <= level["intelligence_to"]:
            return level["id"]
    return None
