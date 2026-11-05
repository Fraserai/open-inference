"""Write the day's snapshot as a short Markdown report."""

LABEL = {"onshore": "In Australia", "mixed": "Australia + overseas", "on_request": "On request",
         "offshore": "Overseas only", "not_offered": "Not offered"}
INLINE = {"onshore": "in Australia", "mixed": "Australia + overseas", "on_request": "on request",
          "offshore": "overseas only", "not_offered": "not offered"}
EVIDENCE = {"per_model_regions": "region listed per model", "provider_statement": "provider's own claim"}
PROVIDER_NAMES = {"scx": "SCX", "resetdata": "ResetData", "xinference": "Xinference", "continuum": "Continuum Labs",
                  "aws_bedrock": "AWS Bedrock"}


def _where(at, statuses=("onshore", "mixed", "on_request")):
    parts = []
    for a in at:
        if a["status"] in statuses:
            parts.append(f"{PROVIDER_NAMES.get(a['provider'], a['provider'])} ({INLINE[a['status']]})")
    return ", ".join(parts) or "–"


def _score(value):
    return f"{value:.1f}" if isinstance(value, (int, float)) else "–"


def render(s):
    out = []
    w = out.append
    top = s["top_open"]
    onshore = [t for t in top if t["best_status"] == "onshore"]
    mixed = [t for t in top if t["best_status"] == "mixed"]
    claimed = [t for t in onshore if all(a["evidence"] == "provider_statement" for a in t["at"] if a["status"] == "onshore")]
    sc = s["scores"]

    w(f"# Open Inference daily report: {s['date']}")
    w("")
    w(f"_Generated {s['generated_at']} UTC. Model scores: Artificial Analysis Intelligence Index as of "
      f"**{sc['as_of']}** ({'live' if sc['status'] == 'live' else 'saved copy: ' + sc.get('detail', '')})._")
    w("")
    w("## Today in one look")
    w(f"- **Top {len(top)} open models processed in Australia somewhere:** {len(onshore)}"
      + (f" ({len(claimed)} of them only on a provider's own claim)" if claimed else "") + ".")
    w(f"- **Listed for Australia *and* overseas, with no documented way to pin to Australia:** {len(mixed)}.")
    w(f"- **Missing in Australia (top {len(top)} open, not processed here):** {len(s['missing'])}.")
    if top:
        best = next((t for t in top if t["best_status"] == "onshore"), None)
        w(f"- **Best open model overall:** {top[0]['name']} ({_score(top[0]['score'])}), "
          f"{INLINE[top[0]['best_status']]}. **Best processed in Australia:** "
          + (f"{best['name']} ({_score(best['score'])}, #{best['rank']})." if best else "none."))
    ch = s.get("changes")
    if ch:
        n = len(ch["added"]) + len(ch["removed"]) + len(ch["status_changed"])
        w(f"- **Changes since {ch['since']}:** {n}" + (" (see below)." if n else "."))
    else:
        w("- **Changes:** first run, nothing to compare yet.")
    w("")

    w(f"## Top {len(top)} open models: where they're processed")
    w("| # | Model | Maker | Score | Australia | Where |")
    w("|---|---|---|---|---|---|")
    for t in top:
        w(f"| {t['rank']} | {t['name']} | {t['creator'] or '–'} | {_score(t['score'])} | {LABEL[t['best_status']]} | {_where(t['at'], tuple(LABEL))} |")
    w("")

    w("## Missing list")
    w(f"Top {len(top)} open models with no provider processing them in Australia:")
    w("")
    for t in s["missing"]:
        extra = f" — {_where(t['at'], ('on_request', 'offshore'))}" if t["at"] else ""
        w(f"- #{t['rank']} {t['name']} ({_score(t['score'])}){extra}")
    w("")

    if ch and (ch["added"] or ch["removed"] or ch["status_changed"] or ch["new_in_top_open"]):
        w(f"## Changes since {ch['since']}")
        for x in ch["added"]:
            w(f"- **Added** at {PROVIDER_NAMES.get(x['provider'], x['provider'])}: {x['model']} ({INLINE[x['status']]})")
        for x in ch["removed"]:
            w(f"- **Gone** from {PROVIDER_NAMES.get(x['provider'], x['provider'])}: {x['model']}")
        for x in ch["status_changed"]:
            w(f"- **Moved** at {PROVIDER_NAMES.get(x['provider'], x['provider'])}: {x['model']}, {INLINE[x['from']]} → {INLINE[x['to']]}")
        for name in ch["new_in_top_open"]:
            w(f"- **New in the top {len(top)}:** {name}")
        if ch["providers_failed"]:
            w(f"- Not compared (a fetch failed on one of the days): {', '.join(ch['providers_failed'])}")
        w("")

    if s["new_open_models"]:
        w("## New open models, not scored yet")
        for m in s["new_open_models"]:
            w(f"- {m['name']} (`{m['weights']}`), listed on OpenRouter {m['listed']}")
        w("")

    w("## Everything processed in Australia")
    w("Every model (open or closed) that a checked provider processes in Australia, or lists for Australia and overseas.")
    w("")
    w("| Model | Open? | Score | Where |")
    w("|---|---|---|---|")
    for e in s["model_map"]:
        if e["best_status"] not in ("onshore", "mixed"):
            continue
        open_ = {True: "open", False: "closed"}.get(e["open_weights"], "?")
        w(f"| {e['name']} | {open_} | {_score(e['score'])} | {_where(e['at'], ('onshore', 'mixed'))} |")
    w("")

    w("## Providers checked")
    w("| Provider | Owner | Models listed | In Australia | AU + overseas | Evidence | Source |")
    w("|---|---|---|---|---|---|---|")
    for p in s["providers"]:
        if p["status"] != "ok":
            w(f"| {p['name']} | {p['owner']} | **failed** | – | – | {p.get('detail', '')} | {p['catalogue'][0]} |")
            continue
        ev = "region per model" if p["id"] in ("scx", "aws_bedrock") else "provider's own claim"
        w(f"| {p['name']} | {p['owner']} | {p['offerings']} | {p['onshore']} | {p['mixed']} | {ev} | {p['catalogue'][0]} |")
    for p in s["providers"]:
        if p.get("note"):
            w(f"- {p['name']}: {p['note']}")
    au_gw = s["openrouter"]["providers_with_au_datacentre"]
    w(f"- OpenRouter providers listing an Australian data centre: {', '.join(g['name'] for g in au_gw) or 'none'}.")
    w("")

    w("## Not checked yet")
    for p in s["not_checked"]:
        w(f"- **{p['name']}**: {p['reason']}")
    w("")

    if s["unmatched"]:
        w("## Names not matched to a score")
        w("Provider model names we couldn't match to an Artificial Analysis entry (often embeddings, audio, or a spelling to add to `tracker/names.py`):")
        w("")
        w(", ".join(s["unmatched"]))
        w("")

    w("## How to read this")
    w("- **In Australia** = an Australia-only region in the provider's docs, AWS in-region or its Australian Geo profile in Sydney/Melbourne, or a provider that says all its serving is in Australia (ResetData, Xinference). Provider claims haven't been checked from outside.")
    w("- **Australia + overseas** = SCX lists the model for AU and other regions, and its docs don't say how to pin a request to AU.")
    w("- **Overseas only** = offered, but processed outside Australia (e.g. SCX models not in its AU table, AWS Global-only models).")
    w("- Scores are a snapshot of the Artificial Analysis Intelligence Index; its versions are rescaled from time to time, so compare ranks rather than raw points across versions.")
    if sc["status"] != "live":
        w("- **To get live scores:** add a free `ARTIFICIAL_ANALYSIS_API_KEY` to `~/open-inference/.env`.")
    w(f"- {s['attribution']}")
    return "\n".join(out) + "\n"
