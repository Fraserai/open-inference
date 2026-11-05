import unittest

from tracker import build, names, providers, report, scores

SCX_HTML = """
<h2>Available in Australia</h2>
<table><thead><tr><th>Model</th><th>Type</th><th>Provider</th><th>Regions</th></tr></thead>
<tbody>
<tr><td>Qwen3-32B</td><td>Language</td><td>Alibaba</td><td><div><span>AU</span></div></td></tr>
<tr><td>MiniMax-M3</td><td>Language</td><td>MiniMax</td><td><span>US</span><span>AU</span></td></tr>
</tbody></table>
<div data-slot="card"><div data-slot="card-title" class="x">Qwen3-32B</div></div>
<div data-slot="card"><div data-slot="card-title"><span>GLM-5.3</span></div></div>
<script>var x = "<div data-slot='card-title'>Ignored</div>";</script>
"""

RESETDATA_HTML = """
<table><tr><th>Category</th><th>Endpoint</th></tr><tr><td>llm</td><td>/chat/completions</td></tr></table>
<table><tr><th>Model</th><th>Category</th><th>Called via</th></tr>
<tr><td><code>zai/glm-5.2</code></td><td>llm</td><td>/chat/completions</td></tr>
<tr><td>meta/llama-3.1-8b-instruct</td><td>llm</td><td>/chat/completions</td></tr></table>
"""

XINFERENCE_HTML = """
<table><tr><th>Model</th><th>What it's for</th><th>Price per 1M tokens</th></tr>
<tr><td>Kimi K3</td><td>Reasoning</td><td>$3.00 in / $15.00 out</td></tr>
<tr><td>GLM 5.3</td><td>Agents</td><td>On request</td></tr>
<tr><td colspan="3">List prices as of October 2026.</td></tr></table>
"""

YES = '<img src="icon-yes.png" alt="supported"/>'
NO = '<img src="icon-no.png" alt="not-supported"/>'
BEDROCK_HTML = f"""
<h2 id="z">Z.AI</h2>
<table><caption><a href="x">GLM 5</a></caption>
<thead><tr><th>Region</th><th>In-Region (<code>bedrock-runtime</code>)</th><th>Geo</th><th>Global</th></tr></thead>
<tr><td><code>us-east-1</code> (N. Virginia)</td><td>{YES}</td><td>{NO}</td><td>{NO}</td></tr>
<tr><td><code>ap-southeast-2</code> (Sydney)</td><td>{YES}</td><td>{NO}</td><td>{NO}</td></tr></table>
<table><caption>GLM 5.3</caption>
<thead><tr><th>Region</th><th>In-Region</th><th>Geo</th><th>Global</th></tr></thead>
<tr><td><code>ap-southeast-2</code> (Sydney)</td><td>{NO}</td><td>{NO}</td><td>{YES}</td></tr></table>
<h2>Anthropic</h2>
<table><caption>Claude Sonnet 5.5</caption>
<thead><tr><th>Region</th><th>In-Region</th><th>Geo</th><th>Global</th></tr></thead>
<tr><td><code>ap-southeast-4</code> (Melbourne)</td><td>{NO}</td><td>{YES}</td><td>{YES}</td></tr></table>
<table><caption>Not in Australia</caption>
<thead><tr><th>Region</th><th>In-Region</th><th>Geo</th><th>Global</th></tr></thead>
<tr><td><code>eu-west-1</code> (Ireland)</td><td>{YES}</td><td>{NO}</td><td>{NO}</td></tr></table>
"""

PAGES = {
    providers.SCX["catalogue"][0]: SCX_HTML,
    providers.RESETDATA["catalogue"][0]: RESETDATA_HTML,
    providers.XINFERENCE["catalogue"][0]: XINFERENCE_HTML,
    providers.BEDROCK["catalogue"][0]: BEDROCK_HTML,
}

SCORES = {"as_of": "2026-10-23", "source": "test", "models": [
    {"name": "GLM 5.3", "aa_name": "GLM-5.3 (Max)", "creator": "zai", "score": 44.8, "open_weights": True},
    {"name": "Kimi K3", "aa_name": "Kimi K3 (Max)", "creator": "moonshotai", "score": 43.6, "open_weights": True},
    {"name": "GLM 5.2", "aa_name": "GLM-5.2 (Max)", "creator": "zai", "score": 33.7, "open_weights": True},
    {"name": "MiniMax M3", "aa_name": "MiniMax-M3", "creator": "minimax", "score": 29.2, "open_weights": True},
    {"name": "GLM 5", "aa_name": "GLM-5 (Reasoning)", "creator": "zai", "score": 27.9, "open_weights": True},
    {"name": "Qwen 3 32B", "aa_name": "Qwen3 32B (Reasoning)", "creator": "alibaba", "score": 7.3, "open_weights": True},
    {"name": "Claude Sonnet 5.5", "aa_name": "Claude Sonnet 5.5 (Max)", "creator": "anthropic", "score": 56.0, "open_weights": False},
]}


def by_model(offers):
    return {o["model"]: o for o in offers}


class NameTests(unittest.TestCase):
    def test_same_model_different_spellings(self):
        self.assertEqual(names.key("zai/glm-5.2"), names.key("GLM-5.2 (Max)"))
        self.assertEqual(names.key("gemma-4-31B-it"), names.key("Gemma 4 31B"))
        self.assertEqual(names.key("Meta-Llama-3.3-70B-Instruct"), names.key("Llama 3.3 70B"))
        self.assertEqual(names.key("Llama-4-Maverick-17B-128E-Instruct"), names.key("Llama 4 Maverick"))

    def test_different_models_stay_apart(self):
        self.assertNotEqual(names.key("DeepSeek V4.1 Flash"), names.key("DeepSeek V4.1 Flash 1017"))
        self.assertNotEqual(names.key("GLM 5.3"), names.key("GLM 5.3 Flash"))
        self.assertNotEqual(names.key("Claude Opus 4.5"), names.key("Claude Opus 5.4"))

    def test_index_keeps_best_score(self):
        index = names.ScoreIndex([{"name": "X 1", "score": 10}, {"name": "X 1", "aa_name": "X 1 (High)", "score": 20}])
        self.assertEqual(index.find("x-1")["score"], 20)


class ParserTests(unittest.TestCase):
    def test_scx_regions(self):
        offers = by_model(providers.parse_scx(PAGES))
        self.assertEqual(offers["Qwen3-32B"]["status"], "onshore")
        self.assertEqual(offers["MiniMax-M3"]["status"], "mixed")
        self.assertEqual(offers["GLM-5.3"]["status"], "offshore")
        self.assertNotIn("Ignored", offers)
        self.assertEqual(len(offers), 3)

    def test_resetdata(self):
        offers = by_model(providers.parse_resetdata(PAGES))
        self.assertEqual(set(offers), {"zai/glm-5.2", "meta/llama-3.1-8b-instruct"})
        self.assertTrue(all(o["evidence"] == "provider_statement" for o in offers.values()))

    def test_xinference(self):
        offers = by_model(providers.parse_xinference(PAGES))
        self.assertEqual(offers["Kimi K3"]["status"], "onshore")
        self.assertEqual(offers["GLM 5.3"]["status"], "on_request")
        self.assertEqual(len(offers), 2)

    def test_bedrock(self):
        offers = by_model(providers.parse_bedrock(PAGES))
        self.assertEqual(offers["GLM 5"]["status"], "onshore")
        self.assertEqual(offers["GLM 5"]["maker"], "Z.AI")
        self.assertEqual(offers["GLM 5.3"]["status"], "offshore")
        self.assertEqual(offers["Claude Sonnet 5.5"]["status"], "onshore")
        self.assertIn("Geo", offers["Claude Sonnet 5.5"]["basis"])
        self.assertNotIn("Not in Australia", offers)

    def test_missing_table_raises(self):
        with self.assertRaises(ValueError):
            providers.parse_scx({providers.SCX["catalogue"][0]: "<p>redesigned</p>"})


def snapshot(pages=PAGES, previous=None, day="2026-11-04"):
    return build.build(day, pages, {u: "ok" for u in pages}, SCORES, {"status": "fallback", "as_of": "2026-10-23"}, previous)


class BuildTests(unittest.TestCase):
    def test_top_open_and_missing(self):
        s = snapshot()
        top = {t["name"]: t for t in s["top_open"]}
        self.assertEqual(top["GLM 5.3"]["best_status"], "on_request")
        self.assertEqual(top["Kimi K3"]["best_status"], "onshore")
        self.assertEqual(top["MiniMax M3"]["best_status"], "mixed")
        self.assertEqual(top["GLM 5"]["best_status"], "onshore")
        self.assertNotIn("Claude Sonnet 5.5", top)                       # closed
        self.assertEqual([t["name"] for t in s["missing"]], ["GLM 5.3"])
        self.assertEqual([t["rank"] for t in s["top_open"]], list(range(1, len(s["top_open"]) + 1)))

    def test_model_map_merges_providers(self):
        s = snapshot()
        glm53 = next(e for e in s["model_map"] if e["name"] == "GLM 5.3")
        self.assertEqual({a["provider"] for a in glm53["at"]}, {"scx", "xinference", "aws_bedrock"})

    def test_failed_provider_is_reported_not_crashed(self):
        pages = dict(PAGES)
        pages[providers.SCX["catalogue"][0]] = None
        s = build.build("2026-11-04", pages, {u: "ok" for u in PAGES}, SCORES, {"status": "fallback"})
        scx = next(p for p in s["providers"] if p["id"] == "scx")
        self.assertEqual(scx["status"], "failed")
        self.assertEqual(next(t for t in s["top_open"] if t["name"] == "MiniMax M3")["best_status"], "not_offered")

    def test_diff(self):
        before = snapshot(day="2026-11-03")
        pages = dict(PAGES)
        pages[providers.XINFERENCE["catalogue"][0]] = XINFERENCE_HTML.replace("On request", "$1 in / $2 out")
        pages[providers.SCX["catalogue"][0]] = None                       # failed today
        after = build.build("2026-11-04", pages, {u: "ok" for u in PAGES}, SCORES, {"status": "fallback"}, before)
        ch = after["changes"]
        self.assertEqual(ch["status_changed"], [{"provider": "xinference", "model": "GLM 5.3", "from": "on_request", "to": "onshore"}])
        self.assertEqual(ch["removed"], [])                               # SCX failing is not removal
        self.assertEqual(ch["providers_failed"], ["scx"])


class ScoresTests(unittest.TestCase):
    def test_from_aa_response(self):
        body = {"data": [
            {"name": "GLM-5.3 (Max)", "model_creator": {"slug": "zai"}, "evaluations": {"artificial_analysis_intelligence_index": 45}},
            {"name": "Claude Sonnet 5.5", "model_creator": {"slug": "anthropic"}, "evaluations": {"artificial_analysis_intelligence_index": 56}},
            {"name": "No score", "evaluations": {}},
        ]}
        or_models = [{"id": "z-ai/glm-5.3", "name": "Z.ai: GLM 5.3", "hugging_face_id": "zai-org/GLM-5.3"}]
        doc = scores.from_aa_response(body, or_models, SCORES, "2026-11-05")
        got = {m["name"]: m for m in doc["models"]}
        self.assertTrue(got["GLM-5.3 (Max)"]["open_weights"])
        self.assertFalse(got["Claude Sonnet 5.5"]["open_weights"])        # from the previous file
        self.assertNotIn("No score", got)


class ReportTests(unittest.TestCase):
    def test_renders(self):
        text = report.render(snapshot(previous=snapshot(day="2026-11-03")))
        self.assertIn("# Open Inference daily report: 2026-11-04", text)
        self.assertIn("Missing list", text)
        self.assertIn("Xinference (in Australia)", text)


if __name__ == "__main__":
    unittest.main()


class PageTest(unittest.TestCase):
    def test_page_renders_todays_numbers(self):
        import json
        from pathlib import Path
        from tracker import page
        path = sorted(Path(__file__).resolve().parent.parent.glob("data/2026-*/snapshot.json"))[0]
        snap = json.loads(path.read_text())
        body = page.render_body(snap)
        onshore = sum(1 for t in snap["top_open"] if t["best_status"] == "onshore")
        self.assertIn(f"{onshore} of the top {len(snap['top_open'])}</span> open AI models", body)
        self.assertEqual(body.count('class="seat '), len(snap["top_open"]))
        self.assertNotIn("<!doctype", body.lower())
        self.assertTrue(page.render_document(snap).startswith("<!doctype html>"))


class ContinuumTest(unittest.TestCase):
    def test_reads_model_table(self):
        html = """<table><tr><th>Model</th><th>Good for</th><th>Made in</th><th>Sending text</th><th>Receiving text</th></tr>
        <tr><th scope="row">Agent <b>Kimi K2.6</b> · Moonshot AI</th><td>Tools</td><td>China</td><td>$1.35</td><td>$5.70</td></tr>
        <tr><th scope="row">Generalist GPT-OSS 120B · OpenAI</th><td>Work</td><td>United States</td><td>$0.22</td><td>$0.85</td></tr></table>"""
        offers = providers.parse_continuum({providers.CONTINUUM["catalogue"][0]: html})
        self.assertEqual([o["model"] for o in offers], ["Kimi K2.6", "GPT-OSS 120B"])
        self.assertTrue(all(o["status"] == "onshore" and o["evidence"] == "provider_statement" for o in offers))
        self.assertEqual(offers[0]["price_in"], "$1.35")
