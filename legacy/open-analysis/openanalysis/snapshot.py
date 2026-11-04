"""Assemble the dated snapshot from raw source data and write it to disk."""

import csv
import json
import re
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from . import SCHEMA_VERSION, config, fx, metrics
from .match import ArtificialAnalysisIndex, best, intelligence, join_gateways, norm_creator

GLOBAL = "global"
AUSTRALIA = "australia"

HAND_TRANSCRIBED = "hand-transcribed"
AA_API = "artificial_analysis_api"
NO_COST_PER_TASK = ("Artificial Analysis's cost per Intelligence Index task was not available from its API, and there "
                    "is no hand-transcribed file for this date in inputs/cost_per_task/. Left empty rather than estimated.")
# A hand-transcribed figure this far from the API's (after rounding to cents) is reported.
COST_MISMATCH_USD = 0.0051
# Value for money is only reported for models at or above this Intelligence Index.
VALUE_FLOOR = 30

# The ten data points (plus bonus) and the model field each one lives in.
# status: phase_1 = filled, planned = later phase. Point 6 is set per run: phase_1 when
# Artificial Analysis's API supplies it, hand-transcribed or no_source when it does not.
POINTS = [
    (1, "price_aud", "phase_1", GLOBAL,
     "List price per 1M tokens in AUD: input, output and a 3:1 input:output blend. Global USD list price "
     "converted at the RBA daily rate, ex GST. The list price is Vercel AI Gateway's model price; for models "
     "not on Vercel, OpenRouter's with any discount removed; for models on neither, Artificial Analysis's. "
     "cheapest_available is the lowest price actually charged by any provider on either gateway for a "
     "full-precision deployment (FP8 or better, or no quantization stated), with its source. cheapest_quantized "
     "is the same for quantized deployments, with the quantization labelled."),
    (2, "speed_from_australia", "planned", AUSTRALIA, "Output tokens per second measured from Australia."),
    (3, "spend_in_australia", "planned", AUSTRALIA, "Spend on the model by Australian users."),
    (4, "australian_usage", "planned", AUSTRALIA, "What Australians use: share of Australian token volume."),
    (5, "latency_from_australia", "planned", AUSTRALIA, "Time to first token measured from Australia."),
    (6, "cost_per_task_aud", "no_source", GLOBAL,
     "Artificial Analysis's cost per Intelligence Index task (weighted average cost per task, USD), converted "
     "to AUD at the RBA daily rate. Artificial Analysis's own figure, from its beta API "
     "(artificial_analysis_intelligence_index_cost.cost_per_task.total_cost). Each value's source says whether "
     "it came from the API or, as a fallback, was read off Artificial Analysis's chart by hand."),
    (7, "smartest_open", "phase_1", GLOBAL,
     "Artificial Analysis Intelligence Index, whether the weights are open, and rank among open models."),
    (8, "value_aud", "phase_1", GLOBAL,
     f"Intelligence Index points per A$1 of blended token price per 1M tokens, for models scoring {VALUE_FLOOR} "
     "or more. Higher is better value. Based on token price, not cost per task."),
    (9, "open_vs_closed_usage", "planned", AUSTRALIA, "Open versus closed model share of usage."),
    (10, "providers_in_australia", "phase_1", AUSTRALIA,
     "Providers serving the model from Australia, as the gateways list them: Vercel AI Gateway deployments in an "
     "Australian cloud region, at that region's price, and OpenRouter providers that list an Australian datacenter "
     "(OpenRouter does not say which datacenter serves a request, so this is weaker evidence). Prices in AUD, ex GST. "
     "vs_list_price compares the cheapest Australian deployment with the model's list price. A count of 0 means "
     "neither gateway lists an Australian deployment; the model may still be available in Australia directly from a "
     "cloud provider. Null where the model is on neither gateway or provider data was not fetched."),
    ("bonus", "runs_in_australia", "planned", AUSTRALIA, "Whether the model can be run inside Australia."),
]

ATTRIBUTION = [
    {"source": "Artificial Analysis", "url": "https://artificialanalysis.ai/",
     "used_for": "Intelligence Index and cost per Intelligence Index task"},
    {"source": "Reserve Bank of Australia", "url": fx.RBA_PAGE_URL, "used_for": "AUD/USD daily exchange rate"},
    {"source": "Vercel AI Gateway", "url": "https://vercel.com/ai-gateway/models", "used_for": "Model prices and providers"},
    {"source": "OpenRouter", "url": "https://openrouter.ai/models",
     "used_for": "Model prices, providers and open-weights status"},
]

# A score matched from the AA API that differs from OpenRouter's copy of the AA score
# probably means the two refer to different releases or settings; listed for review.
DISAGREEMENT_POINTS = 0.05
# The same model priced this many times apart on the two gateways is listed in the report.
PRICE_GAP_RATIO = 1.5
MIN_PRICED_MODELS = 50
# Matches made on weaker evidence than the model's name, listed for review.
# "FP8 or better". Anything else a provider states (fp4, int4, nvfp4, ...) is a quantized deployment.
# Where a provider states nothing, as for nearly every closed model, the deployment is taken as full precision.
FULL_PRECISION = {"fp8", "fp16", "bf16", "fp32"}
LOW_CONFIDENCE = ("slug", "name_relaxed", "name_relaxed_any_creator")


def _per_1m(value, scale=1e6):
    try:
        number = float(value) * scale
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _openrouter_models(raw):
    """OpenRouter base models, dropping entries that are not a distinct priced model."""
    kept, dropped = [], Counter()
    for model in raw["data"]:
        model_id = model["id"]
        if model_id.startswith("~"):
            dropped["aliases"] += 1
        elif ":" in model_id:
            dropped["variants (:free, :batch, ...)"] += 1
        elif model_id.startswith("openrouter/") or (_per_1m(model["pricing"].get("prompt")) is None):
            dropped["routers"] += 1
        elif "text" not in (model.get("architecture") or {}).get("output_modalities", ["text"]):
            dropped["non_text_output"] += 1
        else:
            kept.append(model)
    return kept, dict(dropped)


def _providers(vercel_endpoints, openrouter_endpoints, openrouter_providers=None):
    """Every provider serving the model on either gateway, with the price each one charges.

    openrouter_providers: {provider name: OpenRouter's provider entry}, for headquarters and datacenters.
    """
    providers = []
    for endpoint in vercel_endpoints or []:
        pricing = endpoint.get("pricing") or {}
        inference_regions = endpoint.get("inference_regions") or []
        regions = sorted({r.get("geo_region") for r in inference_regions if r.get("geo_region")})
        detail = []
        for region in inference_regions:
            # A region can carry its own price; without one the endpoint's price applies.
            region_pricing = region.get("pricing") or pricing
            detail.append({
                "geo_region": region.get("geo_region"),
                "provider_region": region.get("provider_region"),
                "region_scope": region.get("scope"),
                "input_usd_per_1m": _per_1m(region_pricing.get("prompt")),
                "output_usd_per_1m": _per_1m(region_pricing.get("completion")),
                # Price rises past a token threshold; the figures above are the first tier.
                "tiered": bool(region_pricing.get("prompt_tiers") or region_pricing.get("completion_tiers")),
            })
        providers.append({
            "gateway": "vercel",
            "provider": endpoint.get("provider_name"),
            "input_usd_per_1m": _per_1m(pricing.get("prompt")),
            "output_usd_per_1m": _per_1m(pricing.get("completion")),
            "quantization": endpoint.get("quantization"),
            "inference_regions": regions,
            "regions": detail,
        })
    for endpoint in openrouter_endpoints or []:
        if (endpoint.get("status") or 0) < 0:       # OpenRouter marks a down endpoint with a negative status
            continue
        pricing = endpoint.get("pricing") or {}
        listing = (openrouter_providers or {}).get(endpoint.get("provider_name")) or {}
        providers.append({
            "gateway": "openrouter",
            "provider": endpoint.get("provider_name"),
            "tag": endpoint.get("tag"),
            "input_usd_per_1m": _per_1m(pricing.get("prompt")),
            "output_usd_per_1m": _per_1m(pricing.get("completion")),
            # The prices above are what is charged, after this fraction off the provider's list price.
            "discount": pricing.get("discount") or 0,
            "quantization": endpoint.get("quantization"),
            # Countries the provider lists for itself, not for this model; None where OpenRouter gives none.
            "headquarters": listing.get("headquarters"),
            "datacenters": listing.get("datacenters") or None,
        })
    return providers


def _australia(providers, list_price, usd_to_aud):
    """Point 10: deployments of the model in Australia, as the gateways list them.

    Vercel names the cloud region of a deployment and its price there. OpenRouter lists the
    countries a provider has datacenters in, but not which one serves a given request, so
    an OpenRouter provider with an Australian datacenter is labelled as the weaker evidence.
    Returns None when there is no provider data to look in.
    """
    if not providers:
        return None
    deployments = []
    for provider in providers:
        if provider["gateway"] == "vercel":
            for region in provider.get("regions") or []:
                if (region.get("geo_region") or "").lower() == "au":
                    deployments.append({
                        "gateway": "vercel", "provider": provider["provider"],
                        "region": region.get("provider_region") or "au",
                        "basis": "Vercel AI Gateway lists this deployment in an Australian region, at this region's price.",
                        "input_usd_per_1m": region["input_usd_per_1m"], "output_usd_per_1m": region["output_usd_per_1m"],
                        **({"tiered": True} if region.get("tiered") else {}),
                    })
        elif "AU" in (provider.get("datacenters") or []) and not (provider.get("tag") or "").endswith("/flex"):
            deployments.append({
                "gateway": "openrouter", "provider": provider["provider"], "region": "AU",
                "basis": "OpenRouter lists an Australian datacenter for this provider, but not which datacenter "
                         "serves a request.",
                "input_usd_per_1m": provider["input_usd_per_1m"], "output_usd_per_1m": provider["output_usd_per_1m"],
            })

    for deployment in deployments:
        if deployment["input_usd_per_1m"] is not None and deployment["output_usd_per_1m"] is not None:
            input_usd, output_usd = deployment["input_usd_per_1m"], deployment["output_usd_per_1m"]
            deployment.update({
                "input_usd_per_1m": round(input_usd, 6), "output_usd_per_1m": round(output_usd, 6),
                "input_aud_per_1m": round(input_usd * usd_to_aud, 4), "output_aud_per_1m": round(output_usd * usd_to_aud, 4),
                "blended_aud_per_1m": round(metrics.blended(input_usd, output_usd) * usd_to_aud, 4),
            })
    priced = [d for d in deployments if d.get("blended_aud_per_1m")]
    cheapest = min(priced, key=lambda d: d["blended_aud_per_1m"]) if priced else None
    listed = (list_price or {}).get("blended_3to1_per_1m")
    return {
        "scope": AUSTRALIA,
        "count": len(deployments),
        "providers": deployments,
        "cheapest": {k: cheapest[k] for k in ("gateway", "provider", "region", "input_aud_per_1m", "output_aud_per_1m",
                                              "blended_aud_per_1m")} if cheapest else None,
        # What the cheapest Australian deployment costs relative to the model's list price: 0.1 is 10% more.
        "vs_list_price": round(cheapest["blended_aud_per_1m"] / listed - 1, 4) if cheapest and listed else None,
    }


def _quantized(provider):
    stated = (provider.get("quantization") or "unknown").lower()
    return stated != "unknown" and stated not in FULL_PRECISION


def _paid(provider):
    return (provider["input_usd_per_1m"] is not None and provider["output_usd_per_1m"] is not None
            and provider["input_usd_per_1m"] + provider["output_usd_per_1m"] > 0)


def _price(vercel, openrouter, aa_model, providers, usd_to_aud):
    """Point 1: the list price, and next to it the cheapest price the model can be bought at."""
    def aud(input_usd, output_usd):
        return {"input_per_1m": round(input_usd * usd_to_aud, 4), "output_per_1m": round(output_usd * usd_to_aud, 4),
                "blended_3to1_per_1m": round(metrics.blended(input_usd, output_usd) * usd_to_aud, 4)}

    # Each source's list price. A gateway's model-level price is its default provider's.
    by_source, charged = {}, {}

    def add(source, input_usd, output_usd, **extra):
        if input_usd is not None and output_usd is not None:
            by_source[source] = {"input_usd_per_1m": round(input_usd, 6), "output_usd_per_1m": round(output_usd, 6),
                                 "blended_aud_per_1m": aud(input_usd, output_usd)["blended_3to1_per_1m"], **extra}

    if vercel:
        pricing = vercel.get("pricing") or {}
        add("vercel", _per_1m(pricing.get("input")), _per_1m(pricing.get("output")))
        if "vercel" in by_source:
            charged["vercel"] = (by_source["vercel"]["input_usd_per_1m"], by_source["vercel"]["output_usd_per_1m"])
    if openrouter:
        pricing = openrouter.get("pricing") or {}
        input_usd, output_usd = _per_1m(pricing.get("prompt")), _per_1m(pricing.get("completion"))
        if input_usd is not None and output_usd is not None:
            charged["openrouter"] = (input_usd, output_usd)
            # OpenRouter shows the price after any discount it has negotiated. Undo it to get the list price.
            discount = next((p["discount"] for p in providers if p["gateway"] == "openrouter" and p["discount"]
                             and p["input_usd_per_1m"] is not None and p["output_usd_per_1m"] is not None
                             and abs(p["input_usd_per_1m"] - input_usd) < 1e-9
                             and abs(p["output_usd_per_1m"] - output_usd) < 1e-9), 0)
            extra = {"discount_removed": discount} if discount else {}
            add("openrouter", input_usd / (1 - discount), output_usd / (1 - discount), **extra)
    if aa_model:
        pricing = aa_model.get("pricing") or {}
        input_usd = _per_1m(pricing.get("price_1m_input_tokens"), 1)
        output_usd = _per_1m(pricing.get("price_1m_output_tokens"), 1)
        # AA reports 0 for models it has no price for, which is not the same as free.
        if (input_usd or 0) + (output_usd or 0) > 0:
            add("artificial_analysis", input_usd, output_usd)
    if not by_source:
        return None

    order = [s for s in ("vercel", "openrouter", "artificial_analysis") if s in by_source]
    paid = [s for s in order if by_source[s]["blended_aud_per_1m"] > 0]
    source = (paid or order)[0]
    listed = by_source[source]

    # Cheapest way to buy it today: any provider on either gateway, at the price actually
    # charged. OpenRouter's "flex" endpoints are left out: a slower service tier, not the same product.
    offers = [p for p in providers if _paid(p) and not (p.get("tag") or "").endswith("/flex")]
    full = [{"gateway": p["gateway"], "provider": p["provider"], "usd": (p["input_usd_per_1m"], p["output_usd_per_1m"]),
             "quantization": p.get("quantization") or "unknown", **({"discount": p["discount"]} if p.get("discount") else {})}
            for p in offers]
    for gateway, (input_usd, output_usd) in charged.items():
        # No provider list for this gateway (endpoints not fetched): fall back to its model price.
        if input_usd + output_usd > 0 and not any(p["gateway"] == gateway for p in providers):
            full.append({"gateway": gateway, "provider": None, "usd": (input_usd, output_usd), "quantization": "unknown"})

    def cheapest(candidates):
        if not candidates:
            return None
        offer = dict(min(candidates, key=lambda o: metrics.blended(*o["usd"])))
        input_usd, output_usd = offer.pop("usd")
        return {**aud(input_usd, output_usd), "input_usd_per_1m": round(input_usd, 6),
                "output_usd_per_1m": round(output_usd, 6), **offer}

    return {
        "scope": GLOBAL,
        "basis": "list price",
        **aud(listed["input_usd_per_1m"], listed["output_usd_per_1m"]),
        "free": not paid,
        "source": source,
        # Full-precision deployments only; a cheaper quantized one, if any, is reported separately.
        "cheapest_available": cheapest([o for o in full if not _quantized(o)]),
        "cheapest_quantized": cheapest([o for o in full if _quantized(o)]),
        "by_source": by_source,
    }


def _open_weights(model_ids, openrouter, forced):
    for model_id in model_ids:
        if model_id in forced:
            return forced[model_id], "config/overrides.json"
    if openrouter is None:
        return None, "unknown: not listed on OpenRouter"
    repo = openrouter.get("hugging_face_id")
    if repo:
        return True, f"OpenRouter lists weights at huggingface.co/{repo}"
    return False, "OpenRouter lists no public weights"


def _match_intelligence(ids, creator, names, openrouter, aa_index, overrides, disagreements):
    """Find the model's Artificial Analysis entry and score. Returns (aa_model, intelligence block)."""
    copy = (((openrouter or {}).get("benchmarks") or {}).get("artificial_analysis") or {}).get("intelligence_index")
    aa_model = how = None
    considered = 0
    slugs = [i.split("/", 1)[1] for i in ids]
    names = [name for name in names if name]
    if aa_index:
        pinned = next((overrides[i] for i in ids if i in overrides), None)
        aa_model, how, considered = aa_index.lookup(creator, slugs, names, pinned)
        if aa_model is None and copy is not None:
            aa_model, how, considered = aa_index.lookup_by_score(creator, slugs + names, copy)
        elif aa_model is None:
            # Slugs mislead often enough that this is tried only when there is nothing else to go on.
            aa_model, how, considered = aa_index.lookup_slug(creator, slugs)

    direct = intelligence(aa_model) if aa_model else None
    if how in LOW_CONFIDENCE and copy is not None and direct is not None and abs(direct - copy) > DISAGREEMENT_POINTS:
        # A loose match that OpenRouter's copy contradicts: take the release the copy points to, or just the copy.
        aa_model, how, considered = aa_index.lookup_by_score(creator, slugs + names, copy)
        direct = intelligence(aa_model) if aa_model else None
    if direct is not None:
        if copy is not None and abs(direct - copy) > DISAGREEMENT_POINTS:
            disagreements.append({"id": ids[0], "artificial_analysis_name": aa_model["name"], "match": how,
                                  "api_index": direct, "openrouter_copy": copy})
        return aa_model, {
            "scope": GLOBAL, "index": direct, "source": "artificial_analysis_api",
            "artificial_analysis_name": aa_model["name"], "match": how, "entries_considered": considered,
        }
    if copy is not None:
        return aa_model, {"scope": GLOBAL, "index": copy, "source": "artificial_analysis_via_openrouter"}
    return aa_model, None


def _model(*, model_id, name, creator, vercel, openrouter, aa_model, intelligence_block, gateway_match,
           providers, usd_to_aud, forced_open):
    ids = [m["id"] for m in (vercel, openrouter) if m]
    is_open, basis = _open_weights(ids, openrouter, forced_open)
    price = _price(vercel, openrouter, aa_model, providers, usd_to_aud)
    model = {
        "id": model_id,
        "name": name,
        "creator": creator,
        "ids": {
            "vercel": vercel["id"] if vercel else None,
            "openrouter": openrouter["id"] if openrouter else None,
            "artificial_analysis": aa_model["slug"] if aa_model else None,
        },
        "gateway_match": gateway_match,
        # Release date of the Artificial Analysis entry the score comes from.
        "release_date": (aa_model or {}).get("release_date"),
        "on_gateways": bool(ids),
        "open_weights": is_open,
        "open_weights_basis": basis,
        "context_window": (vercel or {}).get("context_window") or (openrouter or {}).get("context_length"),
        "max_output_tokens": (vercel or {}).get("max_tokens")
                             or ((openrouter or {}).get("top_provider") or {}).get("max_completion_tokens"),
        "intelligence": intelligence_block,
        "price_aud": price,
        "cost_per_task_aud": None,
        "smartest_open": None,
        "value_aud": None,
        "spread": {"by_cost_per_task": None, "by_token_price": None},
        # Who serves the model anywhere in the world; the Australian ones are picked out in point 10.
        "providers_global": {"scope": GLOBAL, "providers": providers} if providers else None,
        "providers_in_australia": _australia(providers, price, usd_to_aud),
    }
    for _, field, status, _, _ in POINTS:
        if status == "planned":
            model[field] = None
    return model


def _in_australia(model):
    return bool((model["providers_in_australia"] or {}).get("count"))


def _spread(models, cost_of, cost_field, role, x_label, empty_reason):
    """Spread map over the models that have both a score and a cost, plus per-model dominance."""
    def points(subset):
        return [{"id": m["id"], "cost": cost_of(m), "index": m["intelligence"]["index"],
                 "intelligence": metrics.whole_points(m["intelligence"]["index"])} for m in subset]

    plotted = [m for m in models if m["intelligence"] and cost_of(m)]
    everything, per_model = metrics.spread_map(points(plotted), cost_field)
    available, per_available = metrics.spread_map(points([m for m in plotted if m["on_gateways"]]), cost_field)
    opened, per_open = metrics.spread_map(points([m for m in plotted if m["open_weights"]]), cost_field)
    hosted, per_hosted = metrics.spread_map(points([m for m in plotted if _in_australia(m)]), cost_field)
    for model_id, stats in per_model.items():
        stats["scope"] = GLOBAL
        if model_id in per_available:
            stats["on_available_frontier"] = per_available[model_id]["on_frontier"]
        if model_id in per_open:
            stats["on_open_frontier"] = per_open[model_id]["on_frontier"]
        if model_id in per_hosted:
            stats["on_australian_hosted_frontier"] = per_hosted[model_id]["on_frontier"]
    block = {
        "scope": GLOBAL,
        "role": role,
        "status": "ok" if plotted else "empty",
        "x": x_label,
        "y": "Artificial Analysis Intelligence Index. Stored with the API's decimals; compared in whole points.",
        "all_models": everything,
        "available_models": available,
        "open_models": opened,
        "australian_hosted_models": hosted,
    }
    if not plotted:
        block["reason"] = empty_reason
    return block, per_model


def build(raw, status, snapshot_date, previous_fx=None, cost_per_task=None):
    if not raw.get("vercel_models") and not raw.get("openrouter_models"):
        raise RuntimeError("Neither Vercel AI Gateway nor OpenRouter returned data; no snapshot written")

    rate = fx.resolve(snapshot_date, raw.get("rba_csv"), raw.get("rba_rss"), previous_fx)
    usd_to_aud = 1 / rate["aud_usd"]
    overrides = config.load_json("overrides.json")

    vercel = [m for m in (raw.get("vercel_models") or {"data": []})["data"] if m.get("type") == "language"]
    openrouter, dropped = _openrouter_models(raw["openrouter_models"]) if raw.get("openrouter_models") else ([], {})
    aa_data = (raw.get("artificial_analysis") or {}).get("data")
    aa_index = ArtificialAnalysisIndex(aa_data) if aa_data else None
    vercel_endpoints = raw.get("vercel_endpoints") or {}
    openrouter_endpoints = raw.get("openrouter_endpoints") or {}
    openrouter_providers = {p["name"]: p for p in (raw.get("openrouter_providers") or {}).get("data", [])}

    disagreements, models = [], []
    for row in join_gateways(vercel, openrouter, overrides["gateway_aliases"]):
        on_vercel, on_openrouter = row["vercel"], row["openrouter"]
        ids = [m["id"] for m in (on_vercel, on_openrouter) if m]
        openrouter_name = re.sub(r"^[^:]+:\s*", "", on_openrouter["name"]) if on_openrouter else None
        creator = norm_creator(ids[0].split("/")[0])
        names = [on_vercel["name"] if on_vercel else None, openrouter_name]
        aa_model, block = _match_intelligence(ids, creator, names, on_openrouter, aa_index,
                                              overrides["artificial_analysis_aliases"], disagreements)
        models.append(_model(
            model_id=ids[0], name=on_vercel["name"] if on_vercel else openrouter_name, creator=creator,
            vercel=on_vercel, openrouter=on_openrouter, aa_model=aa_model, intelligence_block=block,
            gateway_match=row["match"],
            providers=_providers(vercel_endpoints.get(on_vercel["id"]) if on_vercel else None,
                                 openrouter_endpoints.get(on_openrouter["id"]) if on_openrouter else None,
                                 openrouter_providers),
            usd_to_aud=usd_to_aud, forced_open=overrides["open_weights"]))

    # Models Artificial Analysis scores that neither gateway lists (unreleased, or
    # sold only by their maker). One row per model, represented by its best setting.
    if aa_index:
        matched = {aa_index.group_of(aa_index.by_slug[m["ids"]["artificial_analysis"]])
                   for m in models if m["ids"]["artificial_analysis"]}
        for group, entries in aa_index.groups.items():
            head = best(entries)
            if group in matched or intelligence(head) is None:
                continue
            models.append(_model(
                model_id=f"aa:{head['slug']}", name=head["name"], creator=group[0], vercel=None, openrouter=None,
                aa_model=head, gateway_match="artificial_analysis_only", providers=[], usd_to_aud=usd_to_aud,
                forced_open=overrides["open_weights"],
                intelligence_block={"scope": GLOBAL, "index": intelligence(head), "source": "artificial_analysis_api",
                                    "artificial_analysis_name": head["name"], "match": "artificial_analysis_only",
                                    "entries_considered": len(entries)}))

    # Point 6. Each figure belongs to one Artificial Analysis entry (a model at one setting),
    # so a model gets the cost of the same entry its score came from. AA's own figure is
    # used; a hand-transcribed one only fills a gap, and is checked against AA's where both exist.
    warnings = []
    api_costs = {}
    for entry in (raw.get("artificial_analysis_costs") or {}).get("data", []):
        cost = ((entry.get("artificial_analysis_intelligence_index_cost") or {}).get("cost_per_task") or {}).get("total_cost")
        if cost:        # null and 0 both mean Artificial Analysis has no figure
            api_costs[entry["slug"]] = cost
    by_hand = {row["artificial_analysis_slug"]: row for row in cost_per_task or []}
    sources_used = Counter()
    for model in models:
        slug = model["ids"]["artificial_analysis"]
        hand = by_hand.get(slug)
        if slug in api_costs:
            usd, source = api_costs[slug], AA_API
            if hand and abs(round(usd + 1e-9, 2) - hand["cost_per_task_usd"]) > COST_MISMATCH_USD:
                warnings.append(f"Cost per task for '{slug}': hand-transcribed {hand['cost_per_task_usd']} "
                                f"differs from Artificial Analysis's API figure {usd}. API figure used.")
        elif hand:
            usd, source = hand["cost_per_task_usd"], HAND_TRANSCRIBED
        else:
            continue
        sources_used[source] += 1
        model["cost_per_task_aud"] = {"scope": GLOBAL, "aud": round(usd * usd_to_aud, 4), "usd": usd, "source": source}
        if hand and hand.get("note"):
            model["cost_per_task_aud"]["note"] = hand["note"]
    matched_slugs = {m["ids"]["artificial_analysis"] for m in models}
    for slug in sorted(set(by_hand) - matched_slugs):
        warnings.append(f"Hand-transcribed cost per task for '{slug}' matches no model in the snapshot and was not used.")
    cost_status = AA_API if sources_used[AA_API] else HAND_TRANSCRIBED if sources_used else "no_source"
    status = {**status, "cost_per_task": {"status": "ok" if sources_used else "missing", "models": dict(sources_used)}}
    if not sources_used:
        status["cost_per_task"]["detail"] = NO_COST_PER_TASK

    # Point 7: rank open models by intelligence.
    scored = [m for m in models if m["intelligence"]]
    open_ranked = sorted((m for m in scored if m["open_weights"]), key=lambda m: -m["intelligence"]["index"])
    open_rank = {m["id"]: position for position, m in enumerate(open_ranked, 1)}
    for model in scored:
        model["smartest_open"] = {
            "scope": GLOBAL,
            "intelligence_index": model["intelligence"]["index"],
            "open_weights": model["open_weights"],
            "rank_among_open": open_rank.get(model["id"]),
        }

    # Point 8 needs both a score and a real (non-zero) price.
    def token_price(model):
        price = model["price_aud"]
        return price["blended_3to1_per_1m"] if price and not price["free"] else None

    valued = [m for m in scored if token_price(m) and m["intelligence"]["index"] >= VALUE_FLOOR]
    for model in valued:
        model["value_aud"] = {"scope": GLOBAL,
                              "index_points_per_aud": round(model["intelligence"]["index"] / token_price(model), 2)}
    by_value = sorted(valued, key=lambda m: -m["value_aud"]["index_points_per_aud"])
    for position, model in enumerate(by_value, 1):
        model["value_aud"]["rank"] = position

    by_cost_per_task, per_task_model = _spread(
        models, lambda m: (m["cost_per_task_aud"] or {}).get("aud"), "cost_per_task_aud", "main",
        "Artificial Analysis cost per Intelligence Index task, AUD", NO_COST_PER_TASK)
    by_token_price, per_price_model = _spread(
        models, token_price, "blended_aud_per_1m", "secondary",
        "List price per 1M tokens, AUD, 3:1 input:output blend. Not cost per task: it ignores how many tokens "
        "a model spends on a task, so it ranks models differently from the main map.",
        "No model has both a score and a price.")
    for model in models:
        model["spread"] = {"by_cost_per_task": per_task_model.get(model["id"]),
                           "by_token_price": per_price_model.get(model["id"])}

    models.sort(key=lambda m: (-(m["intelligence"] or {}).get("index", -1), m["id"]))
    priced = sum(1 for m in models if m["price_aud"])
    if priced < MIN_PRICED_MODELS:
        raise RuntimeError(f"Only {priced} models have a price; refusing to write a thin snapshot")

    aa_status = status.get("artificial_analysis", {})
    if not aa_index:
        warnings.append("Artificial Analysis API not used (" + aa_status.get("detail", aa_status.get("status", "no data"))
                        + "). Intelligence Index values are the copy OpenRouter publishes, so models "
                        "that are not on OpenRouter have no score.")
    if rate["method"] != "rba_f11.1_csv":
        warnings.append(f"Exchange rate came from fallback: {rate['method']}.")
    for name in ("vercel_models", "openrouter_models"):
        if status.get(name, {}).get("status") != "ok":
            warnings.append(f"{name} unavailable: prices come from the other gateway only.")

    price_gaps = []
    for model in models:
        offers = (model["price_aud"] or {}).get("by_source", {})
        vercel_aud = offers.get("vercel", {}).get("blended_aud_per_1m")
        openrouter_aud = offers.get("openrouter", {}).get("blended_aud_per_1m")
        if vercel_aud and openrouter_aud and max(vercel_aud, openrouter_aud) / min(vercel_aud, openrouter_aud) >= PRICE_GAP_RATIO:
            price_gaps.append({"id": model["id"], "vercel_blended_aud_per_1m": vercel_aud,
                               "openrouter_blended_aud_per_1m": openrouter_aud})

    # A Vercel-only row and an OpenRouter-only row resolving to one AA entry are probably
    # the same model under two ids; listed so the pair can be joined in config/overrides.json.
    claims = {}
    for model in models:
        if model["gateway_match"] in ("vercel_only", "openrouter_only") and model["ids"]["artificial_analysis"]:
            claims.setdefault(model["ids"]["artificial_analysis"], []).append(model)
    possible_duplicates = [
        {"artificial_analysis": slug, "ids": sorted(m["id"] for m in rows)} for slug, rows in sorted(claims.items())
        if {m["gateway_match"] for m in rows} == {"vercel_only", "openrouter_only"}]

    def summary_entry(model):
        return {"id": model["id"], "name": model["name"], "intelligence_index": model["intelligence"]["index"],
                "blended_aud_per_1m": (model["price_aud"] or {}).get("blended_3to1_per_1m")}

    hosted = [m for m in models if _in_australia(m)]
    if status.get("openrouter_providers", {}).get("status") != "ok":
        warnings.append("openrouter_providers unavailable: Australian datacenters on OpenRouter were not checked.")

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_date": snapshot_date.isoformat(),
        "generated_at": datetime.now(ZoneInfo(config.TIMEZONE)).isoformat(timespec="seconds"),
        "phase": 1,
        "scope_note": "Every value carries a scope. 'global' means the figure is not specific to Australia: "
                      "a worldwide list price or benchmark, shown in AUD. 'australia' means it is about Australia: "
                      "in Phase 1, deployments in Australia as the gateways list them. Nothing is yet measured from "
                      "Australia.",
        "fx": rate,
        "attribution": ATTRIBUTION,
        "sources": status,
        "points": [{"point": number, "field": field, "scope": scope, "definition": text,
                    "status": state if field != "cost_per_task_aud" else {AA_API: "phase_1"}.get(cost_status, cost_status)}
                   for number, field, state, scope, text in POINTS],
        "summary": {
            "scope": GLOBAL,
            "models": len(models),
            "on_gateways": sum(1 for m in models if m["on_gateways"]),
            "with_price": priced,
            "with_intelligence": len(scored),
            "with_cost_per_task": sum(1 for m in models if m["cost_per_task_aud"]),
            "open_weights": sum(1 for m in models if m["open_weights"]),
            "smartest_open_model": summary_entry(open_ranked[0]) if open_ranked else None,
            "smartest_open_top5": [summary_entry(m) for m in open_ranked[:5]],
            "value_floor_intelligence": VALUE_FLOOR,
            "best_value_top5": [{**summary_entry(m), "index_points_per_aud": m["value_aud"]["index_points_per_aud"]}
                                for m in by_value[:5]],
            "hosted_in_australia": {
                "scope": AUSTRALIA,
                "models": len(hosted),
                "with_intelligence": sum(1 for m in hosted if m["intelligence"]),
                "models_by_intelligence": [
                    {**summary_entry(m), "australian_blended_aud_per_1m":
                        (m["providers_in_australia"]["cheapest"] or {}).get("blended_aud_per_1m"),
                     "australian_providers": sorted({f"{p['provider']} ({p['region']})"
                                                     for p in m["providers_in_australia"]["providers"]})}
                    for m in hosted if m["intelligence"]],
            },
        },
        "spread_map": {
            "definitions": {
                "dominance": "A dominates B when A is at least as smart and no dearer, and better on one of the two. "
                             "Intelligence is compared in whole points, as Artificial Analysis's chart displays it; "
                             "the stored scores keep their decimals.",
                "frontier": "Models that no other model dominates.",
                "cheapest_per_intelligence_level": "The cheapest model scoring at or above each level.",
                "all_models": "Every model with a score and a cost.",
                "available_models": "Only models listed on Vercel AI Gateway or OpenRouter.",
                "open_models": "Only open-weights models.",
                "australian_hosted_models": "Only models a gateway lists as deployed in Australia (point 10). Costs "
                                            "are the same global figures as the other views; the Australian deployment "
                                            "can cost more, see providers_in_australia.vs_list_price.",
            },
            "by_cost_per_task": by_cost_per_task,
            "by_token_price": by_token_price,
        },
        "models": models,
        "report": {
            "warnings": warnings,
            "gateway_match": dict(Counter(m["gateway_match"] for m in models)),
            "intelligence_source": dict(Counter(m["intelligence"]["source"] for m in scored)),
            "intelligence_match": dict(Counter(m["intelligence"].get("match", "openrouter_copy") for m in scored)),
            "openrouter_entries_excluded": dropped,
            "intelligence_disagreements": disagreements,
            "low_confidence_matches": [
                {"id": m["id"], "artificial_analysis_name": m["intelligence"]["artificial_analysis_name"],
                 "match": m["intelligence"]["match"]}
                for m in scored if m["intelligence"].get("match") in LOW_CONFIDENCE],
            "possible_duplicates": possible_duplicates,
            "gateway_price_gaps": price_gaps,
        },
    }


CSV_COLUMNS = [
    "id", "name", "creator", "on_gateways", "open_weights", "intelligence_index", "intelligence_source",
    "input_aud_per_1m", "output_aud_per_1m", "blended_aud_per_1m", "price_source",
    "cheapest_blended_aud_per_1m", "cheapest_gateway", "cheapest_provider",
    "cheapest_quantized_blended_aud_per_1m", "cheapest_quantized_provider", "cheapest_quantized_quantization",
    "cost_per_task_aud", "cost_per_task_source", "cost_per_task_on_frontier", "cost_per_task_dominated_by",
    "value_index_points_per_aud", "token_price_on_frontier", "token_price_dominated_by",
    "vercel_id", "openrouter_id", "artificial_analysis_slug", "scope",
    # Point 10. Scope australia; the columns before these are global.
    "au_provider_count", "au_cheapest_blended_aud_per_1m", "au_cheapest_provider", "au_cheapest_region",
    "au_vs_list_price",
]


def _csv_rows(snapshot):
    yield CSV_COLUMNS
    for model in snapshot["models"]:
        price, score = model["price_aud"] or {}, model["intelligence"] or {}
        spread = model["spread"]["by_token_price"] or {}
        task, task_spread = model["cost_per_task_aud"] or {}, model["spread"]["by_cost_per_task"] or {}
        cheapest = price.get("cheapest_available") or {}
        quantized = price.get("cheapest_quantized") or {}
        australia = model["providers_in_australia"] or {}
        au_cheapest = australia.get("cheapest") or {}
        yield [
            model["id"], model["name"], model["creator"], model["on_gateways"], model["open_weights"],
            score.get("index"), score.get("source"),
            price.get("input_per_1m"), price.get("output_per_1m"), price.get("blended_3to1_per_1m"), price.get("source"),
            cheapest.get("blended_3to1_per_1m"), cheapest.get("gateway"), cheapest.get("provider"),
            quantized.get("blended_3to1_per_1m"), quantized.get("provider"), quantized.get("quantization"),
            task.get("aud"), task.get("source"), task_spread.get("on_frontier"), task_spread.get("dominated_by"),
            (model["value_aud"] or {}).get("index_points_per_aud"),
            spread.get("on_frontier"), spread.get("dominated_by"),
            model["ids"]["vercel"], model["ids"]["openrouter"], model["ids"]["artificial_analysis"], GLOBAL,
            australia.get("count"), au_cheapest.get("blended_aud_per_1m"), au_cheapest.get("provider"),
            au_cheapest.get("region"), australia.get("vs_list_price"),
        ]


def write(snapshot, data_dir):
    directory = data_dir / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False)
    json_path = directory / f"{snapshot['snapshot_date']}.json"
    json_path.write_text(text)
    with open(directory / f"{snapshot['snapshot_date']}.csv", "w", newline="") as handle:
        csv.writer(handle).writerows(_csv_rows(snapshot))
    (data_dir / "latest.json").write_text(text)
    return json_path
