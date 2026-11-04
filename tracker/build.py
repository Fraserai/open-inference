"""Fetch every source, build the day's snapshot, and compare it with the last one."""

import json
from datetime import datetime, timezone

from . import SCHEMA_VERSION, http, providers, scores
from .names import ScoreIndex, key

TOP_N = 30
OPENROUTER_PROVIDERS_URL = "https://openrouter.ai/api/v1/providers"


# --- fetching --------------------------------------------------------------------------

def _safe_name(url):
    return url.split("://", 1)[-1].replace("/", "_").replace("?", "_") or "index"


def fetch_all(raw_dir, offline=False):
    """Download (or, offline, reload) every page. Returns pages {url: text} and status."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    urls = [u for p in providers.CHECKED for u in p["catalogue"]]
    urls += [scores.OPENROUTER_MODELS_URL, OPENROUTER_PROVIDERS_URL]
    pages, status = {}, {}
    for url in urls:
        path = raw_dir / _safe_name(url)
        try:
            if offline:
                pages[url] = path.read_text()
            else:
                pages[url] = http.get(url, timeout=45)
                path.write_text(pages[url])
            status[url] = "ok"
        except Exception as error:
            pages[url] = None
            status[url] = f"failed: {error}"
    return pages, status


# --- building --------------------------------------------------------------------------

def _model_fields(match):
    if not match:
        return {"name": None, "creator": None, "score": None, "open_weights": None}
    return {"name": match["name"], "creator": match.get("creator"),
            "score": match.get("score"), "open_weights": match.get("open_weights")}


def build(day, pages, fetch_status, scores_doc, scores_status, previous=None):
    index = ScoreIndex(scores_doc["models"])

    provider_rows, offerings = [], []
    for p in providers.CHECKED:
        row = {k: p.get(k) for k in ("id", "name", "owner", "how_to_buy", "facts_source", "note")}
        row["catalogue"] = p["catalogue"]
        missing = [u for u in p["catalogue"] if not pages.get(u)]
        if missing:
            row.update(status="failed", detail="; ".join(fetch_status.get(u, "") for u in missing))
        else:
            try:
                offers = p["parser"](pages)
                row.update(status="ok", offerings=len(offers),
                           onshore=sum(1 for o in offers if o["status"] == "onshore"),
                           mixed=sum(1 for o in offers if o["status"] == "mixed"))
                for o in offers:
                    o["matched"] = _model_fields(index.find(o["model"]))
                offerings += offers
            except Exception as error:
                row.update(status="failed", detail=f"parse error: {error}")
        provider_rows.append(row)

    # Model map: one entry per model, across providers.
    models = {}
    for o in offerings:
        m = o["matched"]
        group = ("aa", m["name"]) if m["name"] else ("raw", key(o["model"]))
        entry = models.setdefault(group, {**m, "name": m["name"] or o["model"], "scored": bool(m["name"]), "at": []})
        entry["at"].append({k: o[k] for k in ("provider", "model", "status", "evidence", "basis", "url")})
    for entry in models.values():
        entry["best_status"] = min((a["status"] for a in entry["at"]), key=providers.STATUS_ORDER.get)
    model_map = sorted(models.values(), key=lambda e: (providers.STATUS_ORDER[e["best_status"]], -(e["score"] or 0), e["name"]))

    # Top open models and where each one is processed.
    by_name = {e["name"]: e for e in model_map if e["scored"]}
    ranked = sorted((m for m in scores_doc["models"] if m.get("open_weights")), key=lambda m: -m["score"])
    top_open, seen = [], set()
    for m in ranked:
        name = m["name"]
        if name in seen:
            continue
        seen.add(name)
        here = by_name.get(name)
        top_open.append({"rank": len(top_open) + 1, "name": name, "creator": m.get("creator"), "score": m["score"],
                         "best_status": here["best_status"] if here else "not_offered",
                         "at": here["at"] if here else []})
        if len(top_open) == TOP_N:
            break
    missing = [t for t in top_open if t["best_status"] not in ("onshore", "mixed")]

    # Open models newer than the scores: listed on OpenRouter with weights, not yet scored.
    new_open = []
    or_models = _json(pages.get(scores.OPENROUTER_MODELS_URL), "data")
    if or_models is not None:
        as_of = datetime.fromisoformat(scores_doc["as_of"]).replace(tzinfo=timezone.utc).timestamp()
        for m in or_models:
            if m.get("hugging_face_id") and (m.get("created") or 0) > as_of and not index.find(m.get("name", "")) \
                    and not index.find(m["id"]):
                new_open.append({"name": m.get("name"), "id": m["id"], "weights": m["hugging_face_id"],
                                 "listed": datetime.fromtimestamp(m["created"], timezone.utc).date().isoformat()})

    gateways_au = []
    or_providers = _json(pages.get(OPENROUTER_PROVIDERS_URL), "data")
    if or_providers is not None:
        gateways_au = [{"name": p.get("name"), "headquarters": p.get("headquarters"), "datacenters": p.get("datacenters")}
                       for p in or_providers if "AU" in (p.get("datacenters") or []) or p.get("headquarters") == "AU"]

    snapshot = {
        "schema_version": SCHEMA_VERSION, "date": day,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scores": {"as_of": scores_doc["as_of"], "source": scores_doc["source"], **scores_status},
        "providers": provider_rows, "not_checked": providers.NOT_CHECKED,
        "top_open": top_open, "missing": missing, "model_map": model_map,
        "unmatched": sorted({o["model"] for o in offerings if not o["matched"]["name"]}),
        "new_open_models": new_open,
        "openrouter": {"status": "ok" if or_providers is not None else "failed",
                       "providers_with_au_datacentre": gateways_au},
        "fetch_status": fetch_status,
        "attribution": "Model scores: Artificial Analysis (artificialanalysis.ai).",
    }
    snapshot["changes"] = diff(previous, snapshot) if previous else None
    return snapshot


def _json(text, field):
    if not text:
        return None
    try:
        return json.loads(text)[field]
    except (ValueError, KeyError, TypeError):
        return None


# --- comparing -------------------------------------------------------------------------

def _offer_set(snapshot, providers_ok):
    return {(a["provider"], a["model"]): a["status"]
            for e in snapshot["model_map"] for a in e["at"] if a["provider"] in providers_ok}


def diff(previous, current):
    """What changed since the previous snapshot. Providers that failed on either day are
    left out, so a failed fetch never reads as models disappearing."""
    ok_then = {p["id"] for p in previous["providers"] if p["status"] == "ok"}
    ok_now = {p["id"] for p in current["providers"] if p["status"] == "ok"}
    both = ok_then & ok_now
    before, after = _offer_set(previous, both), _offer_set(current, both)
    added = sorted([{"provider": p, "model": m, "status": s} for (p, m), s in after.items() if (p, m) not in before],
                   key=lambda x: (x["provider"], x["model"]))
    removed = sorted([{"provider": p, "model": m, "status": s} for (p, m), s in before.items() if (p, m) not in after],
                     key=lambda x: (x["provider"], x["model"]))
    moved = sorted([{"provider": p, "model": m, "from": before[(p, m)], "to": s}
                    for (p, m), s in after.items() if (p, m) in before and before[(p, m)] != s],
                   key=lambda x: (x["provider"], x["model"]))
    top_then = {t["name"] for t in previous.get("top_open", [])}
    return {"since": previous["date"], "added": added, "removed": removed, "status_changed": moved,
            "new_in_top_open": [t["name"] for t in current["top_open"] if t["name"] not in top_then],
            "providers_failed": sorted((ok_then | ok_now) - both)}
