"""Australian providers: who they are, where their catalogue is, and how to read it.

Statuses for one model at one provider:
  onshore     processed in Australia (an Australia-only region, or the provider says
              all its serving is in Australia)
  mixed       listed for Australia AND overseas regions; the docs don't say how to pin
              a request to Australia
  offshore    offered, but processed outside Australia
  on_request  the provider says it can serve it on request
Evidence:
  per_model_regions   the provider publishes regions model by model
  provider_statement  the provider says its whole service runs in Australia; nobody has
                      checked that from outside yet
"""

from . import html_tables

STATUS_ORDER = {"onshore": 0, "mixed": 1, "on_request": 2, "offshore": 3}
AU_BEDROCK_REGIONS = {"ap-southeast-2": "Sydney", "ap-southeast-4": "Melbourne"}


def _offer(provider, model, status, evidence, basis, url, **extra):
    return {"provider": provider, "model": model, "status": status, "evidence": evidence,
            "basis": basis, "url": url, **extra}


# --- parsers: page text in, list of offerings out -------------------------------------

def parse_scx(pages):
    """platform.scx.ai/docs/models: an "Available in Australia" table with a Regions column,
    then cards for every model. The page says models not in the table are processed
    outside Australia."""
    url = SCX["catalogue"][0]
    doc = html_tables.parse(pages[url])
    table = html_tables.table_with_header(doc.tables, "Model", "Regions")
    if table is None:
        raise ValueError("SCX: no Model/Regions table found")
    offers, seen = [], set()
    for row in table["rows"][1:]:
        cells = [c["text"] for c in row]
        if len(cells) < 4:
            continue
        model, kind, maker, regions = cells[0], cells[1], cells[2], cells[3].split()
        if "AU" not in regions:
            continue
        seen.add(model)
        if regions == ["AU"]:
            offers.append(_offer("scx", model, "onshore", "per_model_regions",
                                 "SCX docs list this model in Australia only.", url, regions=regions, kind=kind, maker=maker))
        else:
            offers.append(_offer("scx", model, "mixed", "per_model_regions",
                                 f"SCX docs list regions {' '.join(regions)}; no documented way to pin a request to Australia.",
                                 url, regions=regions, kind=kind, maker=maker))
    for title in doc.card_titles:
        if title and title not in seen:
            seen.add(title)
            offers.append(_offer("scx", title, "offshore", "per_model_regions",
                                 "Not in SCX's 'Available in Australia' table, which says such models are processed outside Australia.",
                                 url))
    return offers


def parse_resetdata(pages):
    """docs.resetdata.ai/models/overview: the serverless models table. ResetData describes the
    platform as inference 'on Australian infrastructure'. The full catalogue needs a login."""
    url = RESETDATA["catalogue"][0]
    doc = html_tables.parse(pages[url])
    table = html_tables.table_with_header(doc.tables, "Model", "Category")
    if table is None:
        raise ValueError("ResetData: no Model/Category table found")
    return [_offer("resetdata", row[0]["text"], "onshore", "provider_statement",
                   "Listed as a serverless model; ResetData says the platform runs on Australian infrastructure.",
                   url, kind=row[1]["text"])
            for row in table["rows"][1:] if len(row) >= 2 and row[0]["text"]]


def parse_xinference(pages):
    """xinference.co/model-api.html: 'Served from dedicated GPUs in Australia', one price table."""
    url = XINFERENCE["catalogue"][0]
    doc = html_tables.parse(pages[url])
    table = html_tables.table_with_header(doc.tables, "Model")
    if table is None:
        raise ValueError("Xinference: no Model table found")
    offers = []
    for row in table["rows"][1:]:
        if len(row) < 3:
            continue                                  # footnote rows span the table
        model, price = row[0]["text"], row[2]["text"]
        if "request" in price.lower():
            offers.append(_offer("xinference", model, "on_request", "provider_statement",
                                 "Xinference lists it as available on request.", url, price=price))
        else:
            offers.append(_offer("xinference", model, "onshore", "provider_statement",
                                 "Xinference says these models are served from dedicated GPUs in Australia.", url, price=price))
    return offers


def parse_bedrock(pages):
    """AWS Bedrock 'model support by Region' tables: per model, per region, In-Region / Geo /
    Global. In-Region in Sydney or Melbourne, or the Australian Geo profile, keeps processing
    in Australia. Global-only means AWS may process it anywhere."""
    url = BEDROCK["catalogue"][0]
    doc = html_tables.parse(pages[url])
    offers = []
    for table in doc.tables:
        if not table["caption"] or not table["rows"]:
            continue
        header = [c["text"].split(" (")[0] for c in table["rows"][0]]
        local, global_only = [], []
        for row in table["rows"][1:]:
            region = row[0]["text"].split()[0] if row[0]["text"] else ""
            if region not in AU_BEDROCK_REGIONS:
                continue
            marks = dict(zip(header[1:], ["supported" in c["alts"] for c in row[1:]]))
            if marks.get("In-Region") or marks.get("Geo"):
                how = "in-region" if marks.get("In-Region") else "Australian Geo profile"
                local.append(f"{AU_BEDROCK_REGIONS[region]} ({how})")
            elif marks.get("Global"):
                global_only.append(AU_BEDROCK_REGIONS[region])
        maker = table["heading"] or ""
        if local:
            offers.append(_offer("aws_bedrock", table["caption"], "onshore", "per_model_regions",
                                 "AWS lists it " + ", ".join(local) + ".", url, maker=maker, regions=local))
        elif global_only:
            offers.append(_offer("aws_bedrock", table["caption"], "offshore", "per_model_regions",
                                 "Callable from " + "/".join(global_only) + " only through Bedrock's Global profile, which may process it outside Australia.",
                                 url, maker=maker))
    if not offers:
        raise ValueError("Bedrock: no region tables found")
    return offers


def parse_continuum(pages):
    """continuumlabs.ai/models: one table (Model | Good for | Made in | prices...). The model cell
    reads "<Role> <Model name> · <Maker>", e.g. "Agent Kimi K2.6 · Moonshot AI". The page says
    every model on it runs on Continuum's computers in Australia."""
    url = CONTINUUM["catalogue"][0]
    doc = html_tables.parse(pages[url])
    table = html_tables.table_with_header(doc.tables, "Model", "Made in")
    if table is None:
        raise ValueError("Continuum: no Model/Made in table found")
    offers = []
    for row in table["rows"][1:]:
        cell = row[0]["text"]
        head = cell.split(" · ")[0].strip()
        parts = head.split(" ", 1)
        if len(parts) != 2:
            raise ValueError(f"Continuum: unexpected model cell {cell!r}")
        role, model = parts
        maker = cell.split(" · ", 1)[1].strip() if " · " in cell else ""
        offers.append(_offer("continuum", model, "onshore", "provider_statement",
                             "Continuum says every model on its models page runs on its computers in Australia.",
                             url, maker=maker, role=role,
                             price_in=row[3]["text"] if len(row) > 3 else None,
                             price_out=row[4]["text"] if len(row) > 4 else None))
    if not offers:
        raise ValueError("Continuum: models table is empty")
    return offers


# --- the registry ---------------------------------------------------------------------
# Facts are as published on the cited pages, checked 2026-11-04. "unknown" means not checked.

SCX = {
    "id": "scx", "name": "SCX.ai", "parser": parse_scx,
    "catalogue": ["https://platform.scx.ai/docs/models"],
    "owner": "SCX.ai, ASX-listed Australian company",
    "how_to_buy": "Pay-per-token API (OpenAI-compatible), plus dedicated deployments",
    "facts_source": "https://platform.scx.ai/docs/models",
}
RESETDATA = {
    "id": "resetdata", "name": "ResetData", "parser": parse_resetdata,
    "catalogue": ["https://docs.resetdata.ai/models/overview/"],
    "owner": "ResetData (Centuria Capital owns 50%, per press coverage)",
    "how_to_buy": "Serverless pay-per-token API in AUD; dedicated GPUs by enquiry",
    "facts_source": "https://docs.resetdata.ai/models/overview/",
    "note": "Only the serverless list is public; the full catalogue needs a login.",
}
XINFERENCE = {
    "id": "xinference", "name": "Xinference", "parser": parse_xinference,
    "catalogue": ["https://xinference.co/model-api.html"],
    "owner": "Xinference (says it is Australian; not checked)",
    "how_to_buy": "Pay-per-token API; dedicated inference",
    "facts_source": "https://xinference.co/model-api.html",
}
CONTINUUM = {
    "id": "continuum", "name": "Continuum Labs", "parser": parse_continuum,
    "catalogue": ["https://www.continuumlabs.ai/models"],
    "owner": "Continuum Labs Pty Ltd, Melbourne (says it is Australian owned)",
    "how_to_buy": "Pay-per-token API (OpenAI-compatible) in AUD",
    "facts_source": "https://www.continuumlabs.ai/models",
}
BEDROCK = {
    "id": "aws_bedrock", "name": "AWS Bedrock (Sydney, Melbourne)", "parser": parse_bedrock,
    "catalogue": ["https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html"],
    "owner": "Amazon Web Services (US-owned hyperscaler)",
    "how_to_buy": "Pay-per-token in AWS regions ap-southeast-2 and ap-southeast-4",
    "facts_source": "https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html",
}

CHECKED = [SCX, RESETDATA, XINFERENCE, CONTINUUM, BEDROCK]

# Known, but no machine-readable model list yet. Each says why.
NOT_CHECKED = [
    {"id": "azure", "name": "Microsoft Azure AI Foundry (Australia East)",
     "reason": "Region availability isn't in a table we can read reliably yet.",
     "url": "https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure"},
    {"id": "google_vertex", "name": "Google Vertex AI (australia-southeast1)",
     "reason": "Region availability isn't in a table we can read reliably yet.",
     "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations"},
    {"id": "amaze", "name": "Amaze", "coming": True,
     "reason": "Lists 34 open models for Sydney and Melbourne, all marked coming soon (checked 2026-11-05).",
     "url": "https://www.amaze.au/ai-models/"},
    {"id": "groq", "name": "Groq", "coming": True,
     "reason": "Runs a 4.5MW inference site at Equinix Sydney (Nov 2025), but publishes no way to keep requests in Sydney.",
     "url": "https://groq.com/newsroom/groq-expands-to-asia-pacific-with-sydney-data-center-to-power-the-next-generation-of-ai-inference"},
    {"id": "sharon_ai", "name": "Sharon AI", "coming": True,
     "reason": "Australian GPU cloud with an inference engine; no public list of hosted models (checked 2026-11-05).",
     "url": "https://sharonai.com/ai-cloud/"},
    {"id": "data_global", "name": "Data Global", "coming": True,
     "reason": "DGX B300 cluster at Micron21 for a 'Token Factory' inference platform, not launched yet.",
     "url": "https://www.prnewswire.com/apac/news-releases/data-global-pty-ltd-enters-australian-market-with-dgx-b300-ai-server-cluster-at-micron21-data-centre-302927579.html"},
    {"id": "micron21", "name": "Micron21 (mCloud)", "reason": "Sells GPUs to run your own models; no hosted model list.",
     "url": "https://www.micron21.com/enterprise/mcloud-gpu-nvidia-rtx-pro-6000"},
    {"id": "northstar", "name": "NorthStar",
     "reason": "Says it serves Gemma 3 from South Australia; no official site or API domain we could confirm.", "url": ""},
    {"id": "datacom", "name": "Datacom", "reason": "No public model catalogue found.", "url": "https://datacom.com"},
    {"id": "sovereign_australia_ai", "name": "Sovereign Australia AI",
     "reason": "Builds Australian models; no public inference catalogue found.", "url": ""},
]
