"""Render the day's snapshot as the public web page.

render_body(snapshot)     page content only (what the claude.ai Artifact publishes; it adds its own skeleton)
render_document(snapshot) the same content as a complete HTML document (for any static host)

One simple split on the page: a model runs in Australia, or it doesn't. "Runs in Australia"
means at least one checked provider processes it only in Australia. Listed for Australia *and*
overseas with no way to lock it to Australia counts as not here. The detail (which provider,
on whose word) is one tap away on each tile. Everything comes from the snapshot.
"""

import json
from datetime import date
from html import escape

from .report import PROVIDER_NAMES

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MAKERS = {"xiaomi": "Xiaomi", "deepseek": "DeepSeek", "zai": "Z.ai", "stepfun": "StepFun", "moonshotai": "Moonshot",
          "alibaba": "Alibaba", "meta": "Meta", "minimax": "MiniMax", "nvidia": "NVIDIA", "tencent": "Tencent",
          "thinkingmachines": "Thinking Machines", "inclusionai": "InclusionAI", "anthropic": "Anthropic"}
WHERE = {"onshore": "In Australia", "mixed": "Australia or overseas",
         "on_request": "On request", "offshore": "Overseas only"}

CSS = """
/* Layout: floating glass panes over a slow coloured aura; hero number, a 30-tile board, three cards. */
:root {
  --base: #eef2f7; --ink: #0b1220; --soft: #4b5567; --faint: #8a93a3;
  --glass: rgba(255,255,255,.52); --glass-strong: rgba(255,255,255,.72); --edge: rgba(255,255,255,.75);
  --spec: rgba(255,255,255,.95); --shade: rgba(20,32,60,.10);
  --here: #1f9d55; --here-glass: rgba(52,199,89,.20); --here-edge: rgba(52,199,89,.55);
  --aura-1: #7cc4ff; --aura-2: #a7f0d0; --aura-3: #ffc59a;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --base: #05080f; --ink: #f2f5fa; --soft: #aab3c2; --faint: #6f7889;
  --glass: rgba(28,34,46,.46); --glass-strong: rgba(36,42,56,.72); --edge: rgba(255,255,255,.14);
  --spec: rgba(255,255,255,.22); --shade: rgba(0,0,0,.45);
  --here: #30d158; --here-glass: rgba(48,209,88,.18); --here-edge: rgba(48,209,88,.5);
  --aura-1: #1d4e89; --aura-2: #0f5c4a; --aura-3: #6b3a1c; color-scheme: dark; } }
:root[data-theme="dark"] {
  --base: #05080f; --ink: #f2f5fa; --soft: #aab3c2; --faint: #6f7889;
  --glass: rgba(28,34,46,.46); --glass-strong: rgba(36,42,56,.72); --edge: rgba(255,255,255,.14);
  --spec: rgba(255,255,255,.22); --shade: rgba(0,0,0,.45);
  --here: #30d158; --here-glass: rgba(48,209,88,.18); --here-edge: rgba(48,209,88,.5);
  --aura-1: #1d4e89; --aura-2: #0f5c4a; --aura-3: #6b3a1c; color-scheme: dark; }

body { background: var(--base); color: var(--ink); font-family: var(--font); font-size: 16px; line-height: 1.45;
  -webkit-font-smoothing: antialiased; }
.aura { position: fixed; inset: -20vmax; z-index: 0; pointer-events: none; filter: blur(60px); opacity: .9;
  background:
    radial-gradient(38vmax 30vmax at 18% 22%, var(--aura-1), transparent 70%),
    radial-gradient(34vmax 28vmax at 82% 30%, var(--aura-2), transparent 70%),
    radial-gradient(40vmax 30vmax at 55% 88%, var(--aura-3), transparent 70%); }
@media (prefers-reduced-motion: no-preference) {
  .aura { animation: drift 28s ease-in-out infinite alternate; }
  @keyframes drift { to { transform: translate3d(3vmax, -2vmax, 0) rotate(8deg); } }
}
.wrap { position: relative; z-index: 1; max-width: 980px; margin: 0 auto; display: grid; gap: 22px;
  padding-block: 20px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }

.glass { background: var(--glass); border: 1px solid var(--edge); border-radius: 28px;
  -webkit-backdrop-filter: blur(28px) saturate(180%); backdrop-filter: blur(28px) saturate(180%);
  box-shadow: inset 0 1px 0 var(--spec), inset 0 -1px 0 rgba(255,255,255,.06), 0 10px 40px var(--shade); }

.bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 10px 12px 10px 18px; border-radius: 999px; }
.brand { font-weight: 700; letter-spacing: -.01em; font-size: 17px; display: flex; align-items: center; gap: 8px; }
.brand i { width: 10px; height: 10px; border-radius: 50%; background: var(--here); box-shadow: 0 0 12px var(--here); }
.date { font-size: 13px; color: var(--soft); padding: 6px 12px; border-radius: 999px; background: var(--glass-strong); }

.hero { padding: clamp(24px, 5vw, 48px); display: grid; gap: 10px; }
.kicker { font-size: 13px; font-weight: 600; color: var(--soft); letter-spacing: .02em; }
.big { display: flex; align-items: baseline; gap: 6px; line-height: .9; font-weight: 800; letter-spacing: -.045em; }
.big b { font-size: clamp(96px, 20vw, 188px); background: linear-gradient(180deg, var(--ink), var(--here));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.big span { font-size: clamp(40px, 8vw, 72px); color: var(--faint); }
h1 { margin: 0; font-size: clamp(26px, 4.4vw, 40px); font-weight: 700; letter-spacing: -.025em; line-height: 1.1;
  text-wrap: balance; max-width: 20ch; }
.lede { margin: 6px 0 0; color: var(--soft); font-size: 17px; max-width: 56ch; }

.section { padding: clamp(18px, 3.5vw, 28px); display: grid; gap: 16px; min-width: 0; }
h2 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
.sub { margin: -8px 0 0; color: var(--soft); font-size: 14px; }
.key { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--soft); }
.key span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; background: var(--faint); opacity: .6; }
.dot.here { background: var(--here); opacity: 1; box-shadow: 0 0 8px var(--here); }

.board { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); }
.seat { all: unset; box-sizing: border-box; cursor: pointer; display: grid; gap: 4px; min-height: 86px; width: 100%;
  padding: 12px 14px; border-radius: 18px; background: var(--glass-strong); border: 1px solid var(--edge);
  box-shadow: inset 0 1px 0 var(--spec); transition: transform .18s ease, box-shadow .18s ease; }
.seat:hover { transform: translateY(-2px); box-shadow: inset 0 1px 0 var(--spec), 0 8px 24px var(--shade); }
.seat:focus-visible { outline: 2px solid var(--here); outline-offset: 2px; }
.seat .top { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--faint);
  font-family: var(--mono); font-variant-numeric: tabular-nums; }
.seat .m { font-weight: 650; font-size: 15px; line-height: 1.2; overflow-wrap: anywhere; letter-spacing: -.01em; }
.seat .s { font-size: 12px; color: var(--soft); }
.seat.not { opacity: .62; }
.seat.not .m { font-weight: 550; }
.seat.here { background: var(--here-glass); border-color: var(--here-edge); }
.seat.here .s { color: var(--here); font-weight: 600; }

.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.card { padding: 20px; border-radius: 24px; display: grid; gap: 4px; align-content: start; }
.card .k { font-size: 13px; color: var(--soft); font-weight: 600; }
.card .n { font-size: 44px; font-weight: 800; letter-spacing: -.04em; line-height: 1; font-variant-numeric: tabular-nums; }
.card .name { font-size: 30px; font-weight: 750; letter-spacing: -.03em; line-height: 1.1; margin: 2px 0 4px; }
.card .t { font-size: 13px; color: var(--soft); }
.card.here .t b { color: var(--here); }

.list { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.list li { padding: 12px 16px; border-radius: 16px; background: var(--glass-strong); border: 1px solid var(--edge); font-size: 15px; }
.list li small { display: block; color: var(--soft); font-size: 13px; margin-top: 2px; }
.pills { display: flex; flex-wrap: wrap; gap: 8px; }
.pill { display: inline-flex; gap: 8px; align-items: center; padding: 8px 14px; border-radius: 999px; font-size: 14px;
  background: var(--glass-strong); border: 1px solid var(--edge); color: var(--ink); text-decoration: none; }
.pill b { font-variant-numeric: tabular-nums; color: var(--here); }
.pill:hover { box-shadow: 0 6px 18px var(--shade); }
footer { color: var(--soft); font-size: 13px; display: grid; gap: 6px; padding: 4px 8px; }
footer p { margin: 0; max-width: 80ch; }
a { color: inherit; }

dialog { border: 0; padding: 0; background: transparent; color: var(--ink); max-width: min(520px, calc(100vw - 32px)); width: 100%; }
dialog::backdrop { background: rgba(5,10,20,.25); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
.sheet { padding: 22px; display: grid; gap: 12px; background: var(--glass-strong); }
.sheet h3 { margin: 0; font-size: 24px; letter-spacing: -.02em; }
.sheet .meta { color: var(--soft); font-size: 14px; margin-top: -6px; }
.sheet ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.sheet li { display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px; border-radius: 14px;
  background: var(--glass); border: 1px solid var(--edge); font-size: 14px; }
.sheet li span:last-child { color: var(--soft); text-align: right; }
.sheet li.here span:last-child { color: var(--here); font-weight: 600; }
.sheet .note { font-size: 13px; color: var(--soft); margin: 0; }
.close { justify-self: end; all: unset; cursor: pointer; font-size: 14px; font-weight: 600; padding: 8px 16px;
  border-radius: 999px; background: var(--glass); border: 1px solid var(--edge); justify-self: end; }
.close:focus-visible { outline: 2px solid var(--here); outline-offset: 2px; }
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .glass, .sheet { background: var(--glass-strong); } }
"""

SCRIPT = """
(function () {
  var data = JSON.parse(document.getElementById('models').textContent);
  var dlg = document.getElementById('sheet');
  var body = document.getElementById('sheet-body');
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function open(i) {
    var m = data[i];
    var rows = m.at.length ? m.at.map(function (a) {
      return '<li class="' + (a.here ? 'here' : '') + '"><span>' + esc(a.provider) + '</span><span>' + esc(a.where) + '</span></li>';
    }).join('') : '<li><span>No checked provider offers it</span><span>Not in Australia</span></li>';
    body.innerHTML = '<h3>' + esc(m.name) + '</h3><div class="meta">#' + m.rank + ' open model · ' + esc(m.maker) +
      '</div><ul>' + rows + '</ul>';
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
  }
  document.querySelectorAll('.seat').forEach(function (el) {
    el.addEventListener('click', function () { open(+el.dataset.i); });
  });
  document.getElementById('sheet-close').addEventListener('click', function () { dlg.close ? dlg.close() : dlg.removeAttribute('open'); });
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
})();
"""


def _e(value):
    return escape(str(value), quote=True)


def _score(value):
    return f"{value:.1f}" if isinstance(value, (int, float)) else "–"


def _date(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def _here(t):
    return t["best_status"] == "onshore"


def _claim_only(t):
    return all(a["evidence"] == "provider_statement" for a in t["at"] if a["status"] == "onshore")


def _provider(a):
    return PROVIDER_NAMES.get(a["provider"], a["provider"])


def _sheet_rows(t):
    return [{"provider": _provider(a), "where": WHERE.get(a["status"], a["status"]),
             "here": a["status"] == "onshore", "claim": a.get("evidence") == "provider_statement" and a["status"] == "onshore"}
            for a in t["at"]]


def render_body(s):
    top = s["top_open"]
    n = len(top)
    here = [t for t in top if _here(t)]
    claimed = [t for t in here if _claim_only(t)]
    lead_missing = next((i for i, t in enumerate(top) if _here(t)), n)
    closed_here = [e for e in s["model_map"] if e["open_weights"] is False and e["best_status"] == "onshore" and e["score"]]
    best_closed = max(closed_here, key=lambda e: e["score"]) if closed_here else None
    best_open = top[0] if top else None
    best_open_here = here[0] if here else None
    sc = s["scores"]
    out = []
    w = out.append

    w("<title>Open Inference Daily</title>")
    w('<meta name="claude:viewport-fit-sides" content="cover">')
    w('<meta name="description" content="Which of the top open AI models run in Australia, checked every day.">')
    w(f"<style>{CSS}</style>")
    w('<div class="aura" aria-hidden="true"></div>')
    w('<main class="wrap">')

    w('<header class="glass bar"><div class="brand"><i></i>Open Inference</div>'
      f'<div class="date">Updated {_e(_date(s["date"]))}</div></header>')

    # Hero.
    w('<section class="glass hero">')
    w('<div class="kicker">Open AI models in Australia, checked daily</div>')
    w(f'<div class="big" aria-hidden="true"><b>{len(here)}</b><span>/{n}</span></div>')
    w(f"<h1>{len(here)} of the top {n} open models run in Australia.</h1>")
    if lead_missing:
        line = f"None of the top {lead_missing} do." if lead_missing > 1 else "The #1 doesn't."
        w(f'<p class="lede">{_e(line)}</p>')
    w("</section>")

    # Board.
    w('<section class="glass section">')
    w(f"<h2>The top {n}</h2>")
    w('<p class="sub">Ranked smartest first. Tap a model to see who runs it.</p>')
    w('<div class="key"><span><i class="dot here"></i>Runs in Australia</span><span><i class="dot"></i>Not in Australia</span></div>')
    w('<ol class="board">')
    for i, t in enumerate(top):
        h = _here(t)
        w(f'<li><button type="button" class="seat {"here" if h else "not"}" data-i="{i}" '
          f'aria-label="#{t["rank"]} {_e(t["name"])}, {"runs in Australia" if h else "not in Australia"}">'
          f'<span class="top"><span>#{t["rank"]}</span><i class="dot{" here" if h else ""}"></i></span>'
          f'<span class="m">{_e(t["name"])}</span>'
          f'<span class="s">{"In Australia" if h else "Not here"}</span></button></li>')
    w("</ol></section>")

    # Three cards.
    w('<section class="cards">')
    if best_closed:
        w(f'<div class="glass card here"><span class="k">Best AI you can run in Australia</span>'
          f'<span class="name">{_e(best_closed["name"])}</span>'
          f'<span class="t"><b>Runs here</b> on {_e(_onshore_names(best_closed))}</span></div>')
    if best_open:
        w(f'<div class="glass card"><span class="k">Best open model in the world</span>'
          f'<span class="name">{_e(best_open["name"])}</span>'
          f'<span class="t">{"Runs here" if _here(best_open) else "Not in Australia"}</span></div>')
    if best_open_here:
        w(f'<div class="glass card here"><span class="k">Best open model in Australia</span>'
          f'<span class="name">{_e(best_open_here["name"])}</span>'
          f'<span class="t"><b>#{best_open_here["rank"]} in the world</b> · on {_e(_onshore_names(best_open_here))}</span></div>')
    w("</section>")

    # Today.
    w('<section class="glass section">')
    items = _changes(s, n)
    w("<h2>Latest</h2>")
    w('<ul class="list">' + "".join(items) + "</ul>")
    w("</section>")

    # Providers.
    w('<section class="glass section">')
    w("<h2>Providers</h2>")
    w('<p class="sub">Top open models each one runs in Australia.</p>')
    counts = {}
    for t in here:
        for a in t["at"]:
            if a["status"] == "onshore":
                counts[a["provider"]] = counts.get(a["provider"], 0) + 1
    pills = []
    for p in s["providers"]:
        if p["status"] != "ok":
            pills.append(f'<a class="pill" href="{_e(p["catalogue"][0])}">{_e(p["name"])} <span>check failed</span></a>')
        else:
            pills.append(f'<a class="pill" href="{_e(p["catalogue"][0])}">{_e(p["name"])} <b>{counts.get(p["id"], 0)}</b></a>')
    w('<div class="pills">' + "".join(pills) + "</div>")
    w("</section>")

    w("<footer>")
    w("<p>Updated every day. Rankings by Artificial Analysis. Built in Brisbane · @Openinference</p>")
    w("</footer>")
    w("</main>")

    data = [{"name": t["name"], "rank": t["rank"], "maker": MAKERS.get(t["creator"] or "", t["creator"] or "–"),
             "score": _score(t["score"]), "at": _sheet_rows(t)} for t in top]
    w('<dialog id="sheet" aria-label="Where this model runs"><div class="glass sheet">'
      '<div id="sheet-body"></div>'
      '<button type="button" class="close" id="sheet-close">Done</button></div></dialog>')
    w('<script type="application/json" id="models">' + json.dumps(data).replace("</", "<\\/") + "</script>")
    w(f"<script>{SCRIPT}</script>")
    return "\n".join(out) + "\n"


def _short(name):
    return name.split(" (")[0]


def _onshore_names(entry):
    names = [_provider(a) for a in entry["at"] if a["status"] == "onshore"]
    return " and ".join(dict.fromkeys(names)) or "a checked provider"


def _changes(s, n):
    ch = s.get("changes")
    items = []
    if ch:
        for c in ch["added"]:
            where = "runs in Australia" if c["status"] == "onshore" else "not in Australia"
            items.append(f"<li>{_e(_provider(c))} added {_e(c['model'])}<small>{where}</small></li>")
        gone = {}
        for c in ch["removed"]:
            gone.setdefault(_provider(c), []).append(c["model"])
        for prov, models in gone.items():
            head = f"{prov} stopped listing {models[0]}" if len(models) == 1 else f"{prov} stopped listing {len(models)} models"
            items.append(f"<li>{_e(head)}<small>{_e(', '.join(models))}</small></li>")
        for c in ch["status_changed"]:
            now = "now runs in Australia" if c["to"] == "onshore" else "no longer runs in Australia" if c["from"] == "onshore" else "changed where it runs"
            items.append(f"<li>{_e(c['model'])} {now}<small>at {_e(_provider(c))}</small></li>")
        for name in ch["new_in_top_open"]:
            items.append(f"<li>{_e(name)} entered the top {n}</li>")
    today = date.fromisoformat(s["date"])
    for m in s.get("new_open_models", []):
        if (today - date.fromisoformat(m["listed"])).days <= 3:
            items.append(f"<li>New open model: {_e(m['name'].split(': ', 1)[-1])}<small>not ranked yet</small></li>")
    if not items:
        items.append("<li>No changes. Same models, same places.</li>")
    return items


def render_document(s):
    return ('<!doctype html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
            "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n"
            "</head>\n<body>\n" + render_body(s) + "</body>\n</html>\n")
