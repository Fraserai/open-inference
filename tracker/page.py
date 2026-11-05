"""Render the day's snapshot as the public web page.

render_body(snapshot)     page content only (what the claude.ai Artifact publishes; it adds its own skeleton)
render_document(snapshot) the same content as a complete HTML document (for any static host)

Everything on the page comes from the snapshot; nothing is typed in by hand.
"""

from html import escape

from .report import LABEL, PROVIDER_NAMES

STATUS_CLASS = {"onshore": "on", "mixed": "mix", "on_request": "req", "offshore": "off", "not_offered": "none"}
STATUS_SHORT = {"onshore": "In Australia", "mixed": "AU + overseas", "on_request": "On request",
                "offshore": "Overseas only", "not_offered": "Not offered"}
LEGEND = ("onshore", "mixed", "on_request", "offshore", "not_offered")
MAKERS = {"xiaomi": "Xiaomi", "deepseek": "DeepSeek", "zai": "Z.ai", "stepfun": "StepFun", "moonshotai": "Moonshot",
          "alibaba": "Alibaba", "meta": "Meta", "minimax": "MiniMax", "nvidia": "NVIDIA", "tencent": "Tencent",
          "thinkingmachines": "Thinking Machines", "inclusionai": "InclusionAI", "anthropic": "Anthropic",
          "openai": "OpenAI", "google": "Google", "mistral": "Mistral", "amazon": "Amazon"}

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

CSS = """
/* Layout: one reading column; a 30-seat rank board up top, then the evidence tables. */
:root {
  --paper: #f5f7f6; --ink: #14201d; --muted: #5a6b66; --rule: #d6dedb; --panel: #ffffff;
  --accent: #0e6b5c;
  --on: #1f8a4c; --on-bg: #dcf1e3; --mix: #a86a00; --mix-bg: #fbeccc; --req: #3b5fa8; --req-bg: #e0e8f7;
  --off: #b0452a; --off-bg: #f7e0d8; --none: #7b8682; --none-bg: #e7ebe9;
  --display: "Barlow Condensed", "Arial Narrow", "Helvetica Neue", sans-serif;
  --body: "Barlow", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --paper: #0f1615; --ink: #e4ecea; --muted: #93a39e; --rule: #26332f; --panel: #151f1d; --accent: #4cc3a8;
  --on: #5fd18f; --on-bg: #163524; --mix: #e7b04a; --mix-bg: #3a2c10; --req: #8fb0f0; --req-bg: #1d2a45;
  --off: #ee8a6c; --off-bg: #3d1f16; --none: #8d9894; --none-bg: #222b29; color-scheme: dark; } }
:root[data-theme="dark"] {
  --paper: #0f1615; --ink: #e4ecea; --muted: #93a39e; --rule: #26332f; --panel: #151f1d; --accent: #4cc3a8;
  --on: #5fd18f; --on-bg: #163524; --mix: #e7b04a; --mix-bg: #3a2c10; --req: #8fb0f0; --req-bg: #1d2a45;
  --off: #ee8a6c; --off-bg: #3d1f16; --none: #8d9894; --none-bg: #222b29; color-scheme: dark; }
body { background: var(--paper); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5; }
.wrap { max-width: 1060px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 48px; }
a { color: var(--accent); }
a:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.mast { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px 24px;
  border-bottom: 2px solid var(--ink); padding-bottom: 10px; }
.brand { font-family: var(--display); font-weight: 700; font-size: 22px; letter-spacing: .04em; text-transform: uppercase; }
.brand span { color: var(--accent); }
.stamp { font-family: var(--mono); font-size: 13px; color: var(--muted); }
.hero { display: grid; gap: 14px; }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
h1 { font-family: var(--display); font-weight: 700; font-size: clamp(36px, 6.4vw, 64px); line-height: 1.02;
  margin: 0; text-wrap: balance; max-width: 18ch; }
h1 em { font-style: normal; color: var(--accent); }
.lede { font-size: 19px; max-width: 62ch; margin: 0; color: var(--ink); }
.lede b { font-weight: 600; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
.fact { padding: 14px 16px 14px 0; display: grid; gap: 2px; align-content: start; }
.fact + .fact { border-left: 1px solid var(--rule); padding-left: 16px; }
.fact .n { font-family: var(--display); font-weight: 600; font-size: 34px; line-height: 1; font-variant-numeric: tabular-nums; }
.fact .l { font-size: 14px; color: var(--muted); }
@media (max-width: 520px) { .fact + .fact { border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); } }
h2 { font-family: var(--display); font-weight: 600; font-size: 28px; line-height: 1.1; margin: 0; text-wrap: balance; }
section { display: grid; gap: 14px; min-width: 0; }
section > p { margin: 0; max-width: 68ch; color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 8px 16px; font-size: 14px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; list-style: none; margin: 0; padding: 0; }
.seat { display: grid; grid-template-columns: auto 1fr; column-gap: 8px; align-items: baseline; padding: 8px 10px;
  border-radius: 4px; border-left: 4px solid; min-width: 0; }
.seat .r { font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; color: var(--muted); }
.seat .m { font-weight: 600; font-size: 14px; line-height: 1.25; overflow-wrap: anywhere; }
.seat .s { grid-column: 2; font-size: 12px; color: var(--muted); }
.on  { background: var(--on-bg);  border-color: var(--on); }
.mix { background: var(--mix-bg); border-color: var(--mix); }
.req { background: var(--req-bg); border-color: var(--req); }
.off { background: var(--off-bg); border-color: var(--off); }
.none { background: var(--none-bg); border-color: var(--none); }
.sw.on { background: var(--on); } .sw.mix { background: var(--mix); } .sw.req { background: var(--req); }
.sw.off { background: var(--off); } .sw.none { background: var(--none); }
.chip { display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 999px; border: 1px solid; white-space: nowrap; }
.chip.on { color: var(--on); } .chip.mix { color: var(--mix); } .chip.req { color: var(--req); }
.chip.off { color: var(--off); } .chip.none { color: var(--none); }
.claim { font-family: var(--mono); font-size: 11px; color: var(--muted); }
.scroll { overflow-x: auto; border: 1px solid var(--rule); border-radius: 4px; background: var(--panel); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-family: var(--mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); font-weight: 500; white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
td.num { font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
th.num { text-align: right; }
td.where { color: var(--muted); min-width: 220px; }
td.where b { color: var(--ink); font-weight: 600; }
td.model { font-weight: 600; min-width: 150px; }
.compare { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.bar { display: grid; gap: 6px; padding: 14px 16px; background: var(--panel); border: 1px solid var(--rule); border-radius: 4px; }
.bar .k { font-size: 14px; color: var(--muted); }
.bar .v { font-family: var(--display); font-weight: 600; font-size: 22px; line-height: 1.15; }
.track { height: 8px; background: var(--none-bg); border-radius: 4px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--accent); }
.track i.open { background: var(--on); }
.track i.gap { background: var(--off); }
details { border: 1px solid var(--rule); border-radius: 4px; background: var(--panel); }
summary { cursor: pointer; padding: 12px 14px; font-weight: 600; }
details .scroll { border: 0; border-top: 1px solid var(--rule); border-radius: 0; }
ul.plain { margin: 0; padding-left: 20px; display: grid; gap: 4px; max-width: 72ch; }
.changes li b { font-weight: 600; }
footer { border-top: 2px solid var(--ink); padding-top: 12px; display: grid; gap: 8px; font-size: 14px; color: var(--muted); }
footer p { margin: 0; max-width: 80ch; }
@media (prefers-reduced-motion: no-preference) { .track i { transition: width .6s ease; } }
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700'
         '&family=Barlow:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')


def _e(value):
    return escape(str(value), quote=True)


def _score(value):
    return f"{value:.1f}" if isinstance(value, (int, float)) else "–"


def _date(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def _maker(creator):
    return MAKERS.get(creator or "", (creator or "–").title() if creator else "–")


def _where(at, statuses):
    parts = []
    for a in at:
        if a["status"] not in statuses:
            continue
        name = PROVIDER_NAMES.get(a["provider"], a["provider"])
        label = STATUS_SHORT[a["status"]].lower()
        claim = ' <span class="claim">(own claim)</span>' if a.get("evidence") == "provider_statement" else ""
        bold = a["status"] in ("onshore", "mixed")
        parts.append(f"{'<b>' if bold else ''}{_e(name)}{'</b>' if bold else ''} {_e(label)}{claim}")
    return "; ".join(parts) or "No checked provider"


def _chip(status):
    return f'<span class="chip {STATUS_CLASS[status]}">{_e(LABEL[status])}</span>'


def _summary(s):
    top = s["top_open"]
    onshore = [t for t in top if t["best_status"] == "onshore"]
    claimed = [t for t in onshore if all(a["evidence"] == "provider_statement" for a in t["at"] if a["status"] == "onshore")]
    lead_missing = 0
    for t in top:
        if t["best_status"] in ("onshore", "mixed"):
            break
        lead_missing += 1
    best_open_here = onshore[0] if onshore else None
    closed_here = [e for e in s["model_map"] if e["open_weights"] is False and e["best_status"] == "onshore" and e["score"]]
    best_closed_here = max(closed_here, key=lambda e: e["score"]) if closed_here else None
    return {"top": top, "onshore": onshore, "claimed": claimed, "lead_missing": lead_missing,
            "best_open": top[0] if top else None, "best_open_here": best_open_here, "best_closed_here": best_closed_here}


def render_body(s):
    x = _summary(s)
    top, n = x["top"], len(x["top"])
    sc = s["scores"]
    out = []
    w = out.append

    w(f"<title>Open Inference Daily</title>")
    w('<meta name="claude:viewport-fit-sides" content="cover">')
    w(f'<meta name="description" content="Which of the top open AI models are processed in Australia, checked daily.">')
    w(FONTS)
    w(f"<style>{CSS}</style>")
    w('<div class="wrap">')

    w('<header class="mast"><div class="brand">Open <span>Inference</span></div>'
      f'<div class="stamp">Daily report · {_e(_date(s["date"]))} · Brisbane</div></header>')

    # Hero: the thesis, in numbers from today's snapshot.
    w('<section class="hero">')
    w(f'<div class="eyebrow">Open AI models in Australia</div>')
    w(f"<h1><em>{len(x['onshore'])} of the top {n}</em> open models are processed in Australia.</h1>")
    lede = []
    if x["claimed"]:
        lede.append(f"{len(x['claimed'])} of those {len(x['onshore'])} rest on the provider's own claim.")
    if x["lead_missing"]:
        lede.append(f"The top {x['lead_missing']} are all missing." if x["lead_missing"] > 1 else "The #1 model is missing.")
    if x["best_closed_here"]:
        bc = x["best_closed_here"]
        lede.append(f"Meanwhile <b>{_e(bc['name'])}</b>, a closed model, is processed in Sydney and Melbourne on "
                    f"{_e(_where_names(bc['at']))}.")
    w(f'<p class="lede">{" ".join(lede)}</p>')
    w('<div class="facts">')
    w(f'<div class="fact"><span class="n">{len(x["onshore"])}/{n}</span><span class="l">top open models processed here</span></div>')
    w(f'<div class="fact"><span class="n">{len(s["missing"])}</span><span class="l">top open models missing in Australia</span></div>')
    ok = [p for p in s["providers"] if p["status"] == "ok"]
    w(f'<div class="fact"><span class="n">{len(ok)}</span><span class="l">providers checked today ({len(s["not_checked"])} more not yet)</span></div>')
    if x["best_open_here"]:
        b = x["best_open_here"]
        w(f'<div class="fact"><span class="n">#{b["rank"]}</span><span class="l">best open model processed here ({_e(b["name"])})</span></div>')
    w("</div></section>")

    # Rank board.
    w("<section>")
    w(f"<h2>The top {n} open models, by rank</h2>")
    w(f"<p>Ranked by the Artificial Analysis Intelligence Index (as of {_e(_date(sc['as_of']))}). "
      "Each tile shows the best place it can be processed from Australia today.</p>")
    w('<div class="legend">' + "".join(
        f'<span><i class="sw {STATUS_CLASS[k]}"></i>{_e(LABEL[k])}</span>' for k in LEGEND) + "</div>")
    w('<ol class="board">')
    for t in top:
        cls = STATUS_CLASS[t["best_status"]]
        w(f'<li class="seat {cls}" title="{_e(t["name"])}: {_e(LABEL[t["best_status"]])}">'
          f'<span class="r">#{t["rank"]}</span><span class="m">{_e(t["name"])}</span>'
          f'<span class="s">{_e(STATUS_SHORT[t["best_status"]])} · {_score(t["score"])}</span></li>')
    w("</ol></section>")

    # Gap comparison.
    if x["best_open"] and x["best_closed_here"]:
        bo, boh, bc = x["best_open"], x["best_open_here"], x["best_closed_here"]
        hi = max(bc["score"], bo["score"] or 0)
        def bar(label, name, score, cls):
            pct = 100 * (score or 0) / hi
            return (f'<div class="bar"><span class="k">{_e(label)}</span><span class="v">{_e(name)} · {_score(score)}</span>'
                    f'<span class="track"><i class="{cls}" style="width:{pct:.1f}%"></i></span></div>')
        w("<section>")
        w("<h2>Closed vs open, here and anywhere</h2>")
        w("<p>Intelligence Index scores. Higher is smarter. Compare ranks rather than raw points across index versions.</p>")
        w('<div class="compare">')
        w(bar("Best closed model processed in Australia", bc["name"], bc["score"], ""))
        w(bar("Best open model anywhere", bo["name"], bo["score"], "open"))
        if boh:
            own = all(a["evidence"] == "provider_statement" for a in boh["at"] if a["status"] == "onshore")
            w(bar("Best open model processed in Australia" + (" (provider's own claim)" if own else ""),
                  boh["name"], boh["score"], "gap"))
        w("</div></section>")

    # Changes.
    ch = s.get("changes")
    w("<section>")
    if ch:
        items = []
        for c in ch["added"]:
            items.append(f"<li><b>Added</b> at {_e(PROVIDER_NAMES.get(c['provider'], c['provider']))}: {_e(c['model'])} ({_e(STATUS_SHORT[c['status']].lower())})</li>")
        gone = {}
        for c in ch["removed"]:
            gone.setdefault(PROVIDER_NAMES.get(c["provider"], c["provider"]), []).append(c["model"])
        for prov, models in gone.items():
            what = models[0] if len(models) == 1 else f"{len(models)} models: " + ", ".join(models)
            items.append(f"<li><b>No longer listed</b> on {_e(prov)}'s models page: {_e(what)}</li>")
        for c in ch["status_changed"]:
            items.append(f"<li><b>Moved</b> at {_e(PROVIDER_NAMES.get(c['provider'], c['provider']))}: {_e(c['model'])}, "
                         f"{_e(STATUS_SHORT[c['from']].lower())} → {_e(STATUS_SHORT[c['to']].lower())}</li>")
        for name in ch["new_in_top_open"]:
            items.append(f"<li><b>New in the top {n}:</b> {_e(name)}</li>")
        for m in s.get("new_open_models", []):
            items.append(f"<li><b>New open model, not scored yet:</b> {_e(m['name'])} (listed on OpenRouter {_e(_date(m['listed']))})</li>")
        w(f"<h2>What changed since {_e(_date(ch['since']))}</h2>")
        w('<ul class="plain changes">' + ("".join(items) or "<li>Nothing. Same models, same places.</li>") + "</ul>")
        if ch["providers_failed"]:
            w(f"<p>Not compared because a fetch failed on one of the days: {_e(', '.join(ch['providers_failed']))}.</p>")
    else:
        w("<h2>What changed</h2>")
        items = [f"<li><b>New open model, not scored yet:</b> {_e(m['name'])} (listed on OpenRouter {_e(_date(m['listed']))})</li>"
                 for m in s.get("new_open_models", [])]
        w('<ul class="plain changes"><li>First report, so nothing to compare yet.</li>' + "".join(items) + "</ul>")
    w("</section>")

    # Full table.
    w("<section>")
    w(f"<h2>Where each one is processed</h2>")
    w("<p>Every checked provider that offers the model, and where it says the work happens.</p>")
    w('<div class="scroll"><table><thead><tr><th class="num">#</th><th>Model</th><th>Maker</th><th class="num">Score</th>'
      "<th>Australia</th><th>Providers</th></tr></thead><tbody>")
    for t in top:
        w(f'<tr><td class="num">{t["rank"]}</td><td class="model">{_e(t["name"])}</td><td>{_e(_maker(t["creator"]))}</td>'
          f'<td class="num">{_score(t["score"])}</td><td>{_chip(t["best_status"])}</td>'
          f'<td class="where">{_where(t["at"], tuple(LABEL))}</td></tr>')
    w("</tbody></table></div></section>")

    # Everything processed here.
    here = [e for e in s["model_map"] if e["best_status"] in ("onshore", "mixed")]
    w("<section>")
    w("<h2>Everything you can get processed here</h2>")
    w("<details><summary>" + f"{len(here)} models, open and closed, processed in Australia by a checked provider" + "</summary>")
    w('<div class="scroll"><table><thead><tr><th>Model</th><th>Weights</th><th class="num">Score</th><th>Where</th></tr></thead><tbody>')
    for e in here:
        kind = {True: "Open", False: "Closed"}.get(e["open_weights"], "Unknown")
        w(f'<tr><td class="model">{_e(e["name"])}</td><td>{kind}</td><td class="num">{_score(e["score"])}</td>'
          f'<td class="where">{_where(e["at"], ("onshore", "mixed"))}</td></tr>')
    w("</tbody></table></div></details></section>")

    # Providers.
    w("<section>")
    w("<h2>Providers checked</h2>")
    w('<div class="scroll"><table><thead><tr><th>Provider</th><th>Owner</th><th class="num">Models</th>'
      '<th class="num">In Australia</th><th class="num">AU + overseas</th><th>Evidence</th><th>Source</th></tr></thead><tbody>')
    for p in s["providers"]:
        src = p["catalogue"][0]
        if p["status"] != "ok":
            w(f'<tr><td class="model">{_e(p["name"])}</td><td>{_e(p["owner"])}</td><td colspan="4">Fetch failed today</td>'
              f'<td><a href="{_e(src)}">docs</a></td></tr>')
            continue
        ev = "Region listed per model" if p["id"] in ("scx", "aws_bedrock") else "Provider's own claim"
        w(f'<tr><td class="model">{_e(p["name"])}</td><td>{_e(p["owner"])}</td><td class="num">{p["offerings"]}</td>'
          f'<td class="num">{p["onshore"]}</td><td class="num">{p["mixed"]}</td><td>{ev}</td>'
          f'<td><a href="{_e(src)}">docs</a></td></tr>')
    w("</tbody></table></div>")
    notes = [f"<li>{_e(p['name'])}: {_e(p['note'])}</li>" for p in s["providers"] if p.get("note")]
    au_gw = s["openrouter"]["providers_with_au_datacentre"]
    notes.append(f"<li>OpenRouter providers listing an Australian data centre: {_e(', '.join(g['name'] for g in au_gw) or 'none')}.</li>")
    w('<ul class="plain">' + "".join(notes) + "</ul>")
    w("<p><b>Not checked yet:</b> " + _e("; ".join(f"{p['name']} ({p['reason'].rstrip('.').lower()})" for p in s["not_checked"])) + ".</p>")
    w("</section>")

    # Method.
    w("<section>")
    w("<h2>How to read this</h2>")
    w('<ul class="plain">')
    w("<li><b>In Australia</b>: the provider's docs list an Australia-only region for the model, AWS runs it in-region "
      "or through its Australian Geo profile (Sydney and Melbourne), or the provider says all its serving is in Australia "
      "(ResetData, Xinference). Those last claims haven't been tested from outside.</li>")
    w("<li><b>AU + overseas</b>: listed for Australia and other regions, with no documented way to pin a request to Australia.</li>")
    w("<li><b>Overseas only</b>: offered, but processed outside Australia.</li>")
    w("<li><b>Processed in Australia isn't the same as sovereign.</b> AWS is a US company; some local providers sit in "
      "US-owned data centres. The owner column says who runs each one.</li>")
    w(f"<li>Scores: Artificial Analysis Intelligence Index, snapshot of {_e(_date(sc['as_of']))}"
      + ("" if sc["status"] == "live" else " (today's live scores weren't pulled)") + ".</li>")
    w("</ul></section>")

    w("<footer>")
    w(f"<p>Open Inference tracks which AI models are processed in Australia and what it costs to run them here. "
      f"Built in Brisbane. Data checked {_e(_date(s['generated_at']))} from each provider's public docs, linked above. "
      f"Spot a mistake? Tell us on X at @Openinference.</p>")
    w(f"<p>{_e(s['attribution'])} Report generated {_e(s['generated_at'])} UTC.</p>")
    w("</footer>")
    w("</div>")
    return "\n".join(out) + "\n"


def _where_names(at):
    names = [PROVIDER_NAMES.get(a["provider"], a["provider"]) for a in at if a["status"] == "onshore"]
    return " and ".join(dict.fromkeys(names)) or "a checked provider"


def render_document(s):
    return ('<!doctype html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
            "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n"
            "</head>\n<body>\n" + render_body(s) + "</body>\n</html>\n")
