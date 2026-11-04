"""Fetch the three model sources and the RBA rate.

Raw responses are written to data/raw/<date>/ so a snapshot can be rebuilt offline
with --from-raw. A source that fails is recorded in the status block rather than
aborting the run; the snapshot builder decides whether enough data remains.
"""

import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from . import fx, http

AA_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
# Beta endpoint. The only one that carries cost per Intelligence Index task.
AA_COSTS_URL = "https://artificialanalysis.ai/api/v2/language/models/free"
VERCEL_MODELS_URL = "https://ai-gateway.vercel.sh/v1/models"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
# Each provider's headquarters and datacenter countries.
OPENROUTER_PROVIDERS_URL = "https://openrouter.ai/api/v1/providers"

JSON_SOURCES = ("artificial_analysis", "artificial_analysis_costs", "vercel_models", "vercel_endpoints",
                "openrouter_models", "openrouter_endpoints", "openrouter_providers")
TEXT_SOURCES = {"rba_csv": "rba_f11.1.csv", "rba_rss": "rba_exchange_rates.xml"}


def _attempt(raw, status, name, fetch):
    try:
        raw[name] = fetch()
        status[name] = {"status": "ok"}
    except Exception as error:  # a failed source must not take the whole job down
        raw[name] = None
        status[name] = {"status": "failed", "detail": str(error)}


def _endpoints(models_url, model_ids, headers=None):
    """Per-model provider endpoints from a gateway. Both gateways use the same URL shape."""
    def one(model_id):
        url = f"{models_url}/{quote(model_id, safe='/')}/endpoints"
        try:
            return model_id, http.get_json(url, headers=headers, timeout=20, retries=2)["data"]["endpoints"]
        except Exception:
            return model_id, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(one, model_ids))


def _aa_costs(headers):
    """Every page of the beta listing, as {"data": [...]}."""
    rows, page = [], 1
    while True:
        body = http.get_json(f"{AA_COSTS_URL}?page={page}", headers=headers)
        rows += body["data"]
        if not body["pagination"].get("has_more") or page >= 50:
            return {"intelligence_index_version": body.get("intelligence_index_version"), "data": rows}
        page += 1


def collect(skip_endpoints=False):
    raw, status = {}, {}

    aa_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
    if aa_key:
        _attempt(raw, status, "artificial_analysis",
                 lambda: http.get_json(AA_URL, headers={"x-api-key": aa_key}))
        _attempt(raw, status, "artificial_analysis_costs", lambda: _aa_costs({"x-api-key": aa_key}))
    else:
        for name in ("artificial_analysis", "artificial_analysis_costs"):
            raw[name] = None
            status[name] = {"status": "skipped", "detail": "ARTIFICIAL_ANALYSIS_API_KEY not set"}

    _attempt(raw, status, "vercel_models", lambda: http.get_json(VERCEL_MODELS_URL))

    # The model list is public; the key is sent when present so authenticated limits apply.
    or_key = os.environ.get("OPENROUTER_API_KEY")
    or_headers = {"Authorization": f"Bearer {or_key}"} if or_key else {}
    _attempt(raw, status, "openrouter_models", lambda: http.get_json(OPENROUTER_MODELS_URL, headers=or_headers))
    status["openrouter_models"]["authenticated"] = bool(or_key)
    _attempt(raw, status, "openrouter_providers", lambda: http.get_json(OPENROUTER_PROVIDERS_URL, headers=or_headers))

    wanted = {
        "vercel": (VERCEL_MODELS_URL, None, lambda m: m.get("type") == "language"),
        # Aliases (~), variants (:free, :batch) and OpenRouter's own routers are not distinct models.
        "openrouter": (OPENROUTER_MODELS_URL, or_headers,
                       lambda m: not m["id"].startswith(("~", "openrouter/")) and ":" not in m["id"]),
    }
    for gateway, (url, headers, keep) in wanted.items():
        name = f"{gateway}_endpoints"
        if skip_endpoints or not raw[f"{gateway}_models"]:
            raw[name] = None
            status[name] = {"status": "skipped"}
            continue
        ids = [m["id"] for m in raw[f"{gateway}_models"]["data"] if keep(m)]
        endpoints = _endpoints(url, ids, headers)
        failed = sum(1 for value in endpoints.values() if value is None)
        raw[name] = {k: v for k, v in endpoints.items() if v is not None}
        status[name] = {"status": "ok", "models": len(ids), "failed": failed}

    _attempt(raw, status, "rba_csv", lambda: http.get(fx.RBA_CSV_URL))
    _attempt(raw, status, "rba_rss", lambda: http.get(fx.RBA_RSS_URL))
    return raw, status


def save_raw(raw, status, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in JSON_SOURCES:
        if raw.get(name) is not None:
            (directory / f"{name}.json").write_text(json.dumps(raw[name]))
    for name, filename in TEXT_SOURCES.items():
        if raw.get(name) is not None:
            (directory / filename).write_text(raw[name])
    (directory / "status.json").write_text(json.dumps(status, indent=2))


def load_raw(directory):
    raw = {}
    for name in JSON_SOURCES:
        path = directory / f"{name}.json"
        raw[name] = json.loads(path.read_text()) if path.exists() else None
    for name, filename in TEXT_SOURCES.items():
        path = directory / filename
        raw[name] = path.read_text() if path.exists() else None
    status = json.loads((directory / "status.json").read_text())
    return raw, status


def load_cost_per_task(snapshot_date, directory):
    """Hand-transcribed cost per Intelligence Index task for a date, or None if there is no file.

    A fallback for when Artificial Analysis's beta endpoint has no figure: the chart
    is read by hand into inputs/cost_per_task/<date>.csv.
    """
    path = directory / f"{snapshot_date.isoformat()}.csv"
    if not path.exists():
        return None
    with open(path, newline="") as handle:
        return [{**row, "cost_per_task_usd": float(row["cost_per_task_usd"])} for row in csv.DictReader(handle)]
