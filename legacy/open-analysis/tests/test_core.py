import json
import unittest
from datetime import date
from unittest import mock

from openanalysis import check, fx, metrics, snapshot
from openanalysis.match import ArtificialAnalysisIndex, gateway_key, join_gateways, model_name, name_key

RBA_CSV = """F11.1  EXCHANGE RATES
Title,A$1=USD,Trade-weighted Index May 1970 = 100
Series ID,FXRUSD,FXRTWI
07-Oct-2026,0.6970,64.80
08-Oct-2026,0.6956,64.70
09-Oct-2026,0.6979,64.80
12-Oct-2026,,64.90
"""

RBA_RSS = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
         xmlns:cb="http://www.cbwiki.net/wiki/index.php/Specification_1.2/">
  <item><cb:statistics><cb:exchangeRate>
    <cb:observation><cb:value>0.6979</cb:value></cb:observation>
    <cb:targetCurrency>USD</cb:targetCurrency>
    <cb:observationPeriod><cb:period>2026-10-09</cb:period></cb:observationPeriod>
  </cb:exchangeRate></cb:statistics></item>
</rdf:RDF>"""


def aa(name, slug, creator, index, input_price=1.0, output_price=2.0):
    return {"id": slug, "name": name, "slug": slug, "model_creator": {"slug": creator},
            "evaluations": {"artificial_analysis_intelligence_index": index},
            "pricing": {"price_1m_input_tokens": input_price, "price_1m_output_tokens": output_price}}


class FxTest(unittest.TestCase):
    def test_csv_uses_latest_rate_on_or_before_the_date(self):
        self.assertEqual(fx.parse_csv(RBA_CSV, date(2026, 10, 11)), (date(2026, 10, 9), 0.6979))
        self.assertEqual(fx.parse_csv(RBA_CSV, date(2026, 10, 8)), (date(2026, 10, 8), 0.6956))

    def test_csv_skips_days_with_no_rate(self):
        self.assertEqual(fx.parse_csv(RBA_CSV, date(2026, 10, 12))[0], date(2026, 10, 9))

    def test_rss(self):
        self.assertEqual(fx.parse_rss(RBA_RSS), (date(2026, 10, 9), 0.6979))

    def test_resolve_falls_back_in_order(self):
        day = date(2026, 10, 11)
        self.assertEqual(fx.resolve(day, RBA_CSV, RBA_RSS)["method"], "rba_f11.1_csv")
        self.assertEqual(fx.resolve(day, "garbage", RBA_RSS)["method"], "rba_rss")
        previous = {"rate_date": "2026-10-08", "aud_usd": 0.6956}
        carried = fx.resolve(day, None, None, previous)
        self.assertEqual((carried["method"], carried["days_old"]), ("carried_forward_from_previous_snapshot", 3))
        with self.assertRaises(RuntimeError):
            fx.resolve(day, None, None, None)

    def test_usd_to_aud(self):
        self.assertAlmostEqual(fx.resolve(date(2026, 10, 11), RBA_CSV)["usd_to_aud"], 1 / 0.6979, places=5)


class GatewayJoinTest(unittest.TestCase):
    def test_key_ignores_word_order_and_creator_spelling(self):
        self.assertEqual(gateway_key("meta-llama/llama-4-scout"), gateway_key("meta/llama-4-scout"))
        self.assertEqual(gateway_key("alibaba/qwen-3-max"), gateway_key("qwen/qwen3-max"))

    def test_key_keeps_version_order(self):
        self.assertNotEqual(gateway_key("openai/gpt-5.4"), gateway_key("openai/gpt-4.5"))

    def test_plus_is_part_of_the_name(self):
        self.assertNotEqual(name_key("Command A+"), name_key("Command A"))
        self.assertEqual(name_key("Command A+"), name_key("command-a-plus"))

    def test_join(self):
        vercel = [{"id": i} for i in ("anthropic/claude-sonnet-4.5", "meta/llama-3.3-70b", "amazon/nova-lite",
                                      "alibaba/qwen3-max", "alibaba/qwen3-max-preview", "openai/gpt-5-fast")]
        openrouter = [{"id": i} for i in ("anthropic/claude-sonnet-4.5", "meta-llama/llama-3.3-70b-instruct",
                                          "amazon/nova-lite-v1", "qwen/qwen3-max-2512", "microsoft/phi-4")]
        rows = join_gateways(vercel, openrouter, {"amazon/nova-lite": "amazon/nova-lite-v1"})
        how = {(r["vercel"] or {}).get("id") or r["openrouter"]["id"]: r["match"] for r in rows}
        self.assertEqual(how["anthropic/claude-sonnet-4.5"], "exact")
        self.assertEqual(how["meta/llama-3.3-70b"], "relaxed")
        self.assertEqual(how["amazon/nova-lite"], "override")
        # Two Vercel models collapse to the same relaxed key, so neither is guessed at.
        self.assertEqual(how["alibaba/qwen3-max"], "vercel_only")
        self.assertEqual(how["alibaba/qwen3-max-preview"], "vercel_only")
        self.assertEqual(how["openai/gpt-5-fast"], "vercel_only")
        self.assertEqual(how["microsoft/phi-4"], "openrouter_only")


class ArtificialAnalysisMatchTest(unittest.TestCase):
    """Cases taken from the live Artificial Analysis listing of 2026-10-11."""

    def setUp(self):
        self.index = ArtificialAnalysisIndex([
            aa("Claude Opus 4.5 (Reasoning)", "claude-opus-4-5-thinking", "anthropic", 29.1),
            aa("Claude Opus 4.5 (Non-reasoning)", "claude-opus-4-5", "anthropic", 23.7),
            aa("Claude Opus 5.5 (Max, Default Fallback)", "claude-opus-5-5", "anthropic", 57.6),
            aa("Claude Opus 5.5 (Low, Default Fallback)", "claude-opus-5-5-low", "anthropic", 42.3),
            aa("GPT-5 mini (High)", "gpt-5-mini", "openai", 16.8),
            aa("GPT-5 mini (Medium)", "gpt-5-mini-medium", "openai", 20.6),
            aa("GPT-5.2 (xhigh)", "gpt-5-2", "openai", 30.0),
            aa("Qwen3.8 Max (0902)", "qwen3-8-max", "alibaba", 45.4),
            aa("Qwen3.8 Max", "qwen3-8-max-0803", "alibaba", 40.2),
            aa("Grok 4.1 Fast (Reasoning)", "grok-4-1-fast-reasoning", "xai", 22.0),
            aa("Grok 4.1 Fast (Non-reasoning)", "grok-4-1-fast", "xai", 15.0),
            aa("Kimi K3 (Max)", "kimi-k3", "kimi", 43.6),
            aa("Mistral Large 4 Preview", "mistral-large-4", "mistral", 38.4),
            aa("Command A", "command-a", "cohere", 7.0),
            aa("Command A+", "command-a-plus", "cohere", 13.1),
            aa("DeepSeek V4 Pro 0424 (Max)", "deepseek-v4-pro-0424", "deepseek", 30.4),
            aa("DeepSeek V4 Pro 0813 (Max)", "deepseek-v4-pro", "deepseek", 36.0),
            aa("Grok 4.20 0309 v2 (Non-reasoning)", "grok-4-20-non-reasoning", "xai", 18.0),
        ])

    def name(self, *args, **kwargs):
        model, how, _ = self.index.lookup(*args, **kwargs)
        return (model["name"] if model else None), how

    def test_run_settings_are_dropped_but_releases_are_kept(self):
        self.assertEqual(name_key(model_name("Claude Opus 5.5 (Max, Default Fallback)")), name_key("Claude Opus 5.5"))
        self.assertEqual(name_key(model_name("Claude Fable 5 (Max, Opus 4.8 Fallback)")), name_key("Claude Fable 5"))
        self.assertEqual(name_key(model_name("Qwen3.8 Max (0902)")), name_key("Qwen3.8 Max 0902"))

    def test_best_setting_represents_the_model(self):
        # The bare slug is the weaker run in both of these; the chart shows the stronger.
        self.assertEqual(self.name("anthropic", ["claude-opus-4.5"]), ("Claude Opus 4.5 (Reasoning)", "name"))
        self.assertEqual(self.name("openai", ["gpt-5-mini"]), ("GPT-5 mini (Medium)", "name"))
        self.assertEqual(self.index.lookup("anthropic", ["claude-opus-5.5"])[2], 2)

    def test_dated_releases_stay_separate(self):
        self.assertEqual(self.name("alibaba", ["qwen3.8-max-0902"])[0], "Qwen3.8 Max (0902)")
        self.assertEqual(self.name("qwen", ["qwen3.8-max"])[0], "Qwen3.8 Max")

    def test_id_that_names_a_setting(self):
        self.assertEqual(self.name("spacexai", ["grok-4.1-fast-non-reasoning"]),
                         ("Grok 4.1 Fast (Non-reasoning)", "name_with_setting"))

    def test_creator_spelt_differently(self):
        self.assertEqual(self.name("moonshotai", ["kimi-k3"]), ("Kimi K3 (Max)", "name_any_creator"))

    def test_relaxed_match_is_labelled(self):
        self.assertEqual(self.name("mistral", ["mistral-large-4"]), ("Mistral Large 4 Preview", "name_relaxed"))

    def test_plus_models(self):
        self.assertEqual(self.name("cohere", ["command-a"])[0], "Command A")
        self.assertEqual(self.name("cohere", ["command-a-plus"])[0], "Command A+")

    def test_wrong_display_name_is_not_trusted(self):
        # Vercel shows "GPT 5.2" for gpt-5.2-pro; the id says it is a different model.
        self.assertEqual(self.name("openai", ["gpt-5.2-pro"], ["GPT 5.2 "]), (None, None))
        self.assertEqual(self.name("openai", ["gpt-5.2"], ["GPT 5.2"])[0], "GPT-5.2 (xhigh)")

    def test_score_picks_the_dated_release(self):
        # The id does not say which release; unaided, the best one is taken and labelled as loose.
        self.assertEqual(self.name("deepseek", ["deepseek-v4-pro"]), ("DeepSeek V4 Pro 0813 (Max)", "name_relaxed"))
        model, how, _ = self.index.lookup_by_score("deepseek", ["deepseek-v4-pro"], 30.4)
        self.assertEqual((model["name"], how), ("DeepSeek V4 Pro 0424 (Max)", "openrouter_score"))
        self.assertEqual(self.index.lookup_by_score("deepseek", ["deepseek-v4-pro"], 99.0), (None, None, 0))

    def test_slug_and_override(self):
        self.assertEqual(self.name("xai", ["grok-4.20-non-reasoning"]), (None, None))
        model, how, _ = self.index.lookup_slug("xai", ["grok-4.20-non-reasoning"])
        self.assertEqual((model["slug"], how), ("grok-4-20-non-reasoning", "slug"))
        self.assertEqual(self.name("openai", ["anything"], pinned_slug="gpt-5-2"), ("GPT-5.2 (xhigh)", "override"))


class SpreadMapTest(unittest.TestCase):
    def test_blended_and_whole_points(self):
        self.assertEqual(metrics.blended(4.0, 20.0), 8.0)
        self.assertEqual([metrics.whole_points(x) for x in (46.3, 46.4, 30.5, 57.6)], [46, 46, 31, 58])

    def test_spread_map(self):
        points = [
            {"id": "cheap", "cost": 0.1, "intelligence": 12},
            {"id": "mid", "cost": 1.0, "intelligence": 31},
            {"id": "mid_dearer", "cost": 2.0, "intelligence": 31},
            {"id": "top", "cost": 10.0, "intelligence": 47},
            {"id": "overpriced", "cost": 20.0, "intelligence": 12},
        ]
        summary, per_model = metrics.spread_map(points, "aud")
        self.assertEqual([p["id"] for p in summary["frontier"]], ["cheap", "mid", "top"])
        self.assertEqual((summary["models"], summary["dominated"]), (5, 2))
        # mid > mid_dearer, and all four others > overpriced; two of those pairs are at equal intelligence.
        self.assertEqual((summary["dominance_relationships"], summary["same_intelligence_relationships"]), (5, 2))
        self.assertEqual(per_model["mid_dearer"]["dominated_by"], "mid")
        self.assertEqual(per_model["overpriced"]["dominated_by"], "cheap")
        self.assertEqual(per_model["mid"]["dominates_count"], 2)
        self.assertEqual(summary["cheapest_per_intelligence_level"], [
            {"intelligence_from": 0, "intelligence_to": 12, "id": "cheap", "intelligence_index": 12, "aud": 0.1},
            {"intelligence_from": 13, "intelligence_to": 31, "id": "mid", "intelligence_index": 31, "aud": 1.0},
            {"intelligence_from": 32, "intelligence_to": 47, "id": "top", "intelligence_index": 47, "aud": 10.0},
        ])
        self.assertEqual([metrics.cheapest_at_least(summary, level) for level in (0, 12, 13, 47, 48)],
                         ["cheap", "cheap", "mid", "top", None])

    def test_compared_in_whole_points_but_decimals_are_kept(self):
        # 46.3 and 46.4 are both 46 on the chart, so the cheaper one dominates; the data keeps the decimals.
        points = [{"id": "mimo", "cost": 0.13, "index": 46.3, "intelligence": metrics.whole_points(46.3)},
                  {"id": "grok", "cost": 3.74, "index": 46.4, "intelligence": metrics.whole_points(46.4)}]
        summary, per_model = metrics.spread_map(points)
        self.assertEqual(per_model["grok"]["dominated_by"], "mimo")
        self.assertEqual(summary["same_intelligence_relationships"], 1)
        self.assertEqual(summary["frontier"], [{"id": "mimo", "intelligence_index": 46.3, "cost": 0.13}])

    def test_identical_models_do_not_dominate_each_other(self):
        twins = [{"id": "a", "cost": 1.0, "intelligence": 30}, {"id": "b", "cost": 1.0, "intelligence": 30}]
        self.assertEqual(len(metrics.spread_map(twins)[0]["frontier"]), 2)

    def test_empty(self):
        summary, per_model = metrics.spread_map([])
        self.assertEqual((summary["models"], summary["frontier"], per_model), (0, [], {}))


class ReferenceTest(unittest.TestCase):
    def test_method_reproduces_every_hand_checked_reference(self):
        references = sorted(check.REFERENCE_DIR.glob("*.json"))
        self.assertTrue(references)
        for path in references:
            results = check.check_method(json.loads(path.read_text()))
            self.assertEqual([message for state, message in results if state != check.OK], [], path.name)


class SnapshotTest(unittest.TestCase):
    def build(self, with_aa, cost_per_task=None, api_costs=None):
        raw = {
            "rba_csv": RBA_CSV,
            "rba_rss": None,
            "vercel_models": {"data": [
                {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "type": "language",
                 "context_window": 1000000, "max_tokens": 64000, "pricing": {"input": "0.000003", "output": "0.000015"}},
                {"id": "alibaba/qwen3-coder", "name": "Qwen3 Coder", "type": "language",
                 "pricing": {"input": "0.0000015", "output": "0.0000075"}},
                {"id": "openai/text-embedding-3", "name": "Embedding", "type": "embedding", "pricing": {"input": "0.0000001"}},
            ]},
            "vercel_endpoints": {"alibaba/qwen3-coder": [
                {"provider_name": "alibaba", "pricing": {"prompt": "0.0000015", "completion": "0.0000075"},
                 "inference_regions": [{"scope": "specific", "geo_region": "au", "provider_region": "ap-southeast-2",
                                        "pricing": {"prompt": "0.00000165", "completion": "0.00000825"}}]},
                {"provider_name": "vertex", "pricing": {"prompt": "0.00000022", "completion": "0.0000018"},
                 "inference_regions": [{"geo_region": "us"}]},
            ]},
            "openrouter_models": {"data": [
                {"id": "anthropic/claude-sonnet-4.5", "name": "Anthropic: Claude Sonnet 4.5", "hugging_face_id": "",
                 "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                 "benchmarks": {"artificial_analysis": {"intelligence_index": 20.7}}},
                {"id": "qwen/qwen3-coder", "name": "Qwen: Qwen3 Coder", "hugging_face_id": "Qwen/Qwen3-Coder",
                 "pricing": {"prompt": "0.0000003", "completion": "0.000001"},
                 "benchmarks": {"artificial_analysis": {"intelligence_index": 25.0}}},
                {"id": "qwen/qwen3-coder:free", "name": "free", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "openrouter/auto", "name": "Auto", "pricing": {"prompt": "-1", "completion": "-1"}},
            ]},
            "artificial_analysis": {"data": [
                aa("Claude 4.5 Sonnet (Non-reasoning)", "claude-4-5-sonnet", "anthropic", 18.0, 3.0, 15.0),
                aa("Claude 4.5 Sonnet (Reasoning)", "claude-4-5-sonnet-thinking", "anthropic", 30.0, 3.0, 15.0),
                aa("Gemini 4 Argon (High)", "gemini-4-argon", "google", 52.6, 2.0, 10.0),
                aa("Gemini 4 Argon (Low)", "gemini-4-argon-low", "google", 40.0, 2.0, 10.0),
                aa("K2 Horizon", "k2-horizon", "ifm", 30.5, 0, 0),
            ]} if with_aa else None,
        }
        raw["artificial_analysis_costs"] = {"data": [
            {"slug": slug, "artificial_analysis_intelligence_index_cost": cost and {"cost_per_task": {"total_cost": cost}}}
            for slug, cost in api_costs.items()]} if api_costs else None
        status = {"artificial_analysis": {"status": "ok" if with_aa else "skipped", "detail": "no key"},
                  "vercel_models": {"status": "ok"}, "openrouter_models": {"status": "ok"},
                  "openrouter_providers": {"status": "ok"}}
        with mock.patch.object(snapshot, "MIN_PRICED_MODELS", 1):
            return snapshot.build(raw, status, date(2026, 10, 11), cost_per_task=cost_per_task)

    def test_without_artificial_analysis_key(self):
        result = self.build(with_aa=False)
        models = {m["id"]: m for m in result["models"]}
        self.assertEqual(set(models), {"anthropic/claude-sonnet-4.5", "alibaba/qwen3-coder"})

        sonnet = models["anthropic/claude-sonnet-4.5"]
        self.assertEqual(sonnet["intelligence"]["source"], "artificial_analysis_via_openrouter")
        self.assertAlmostEqual(sonnet["price_aud"]["input_per_1m"], 3 / 0.6979, places=3)
        self.assertEqual(sonnet["price_aud"]["scope"], "global")
        self.assertIs(sonnet["open_weights"], False)
        self.assertIsNone(sonnet["speed_from_australia"])

        coder = models["alibaba/qwen3-coder"]
        self.assertIs(coder["open_weights"], True)
        # Headline is the list price (Vercel's model price); the cheapest offer sits alongside with its source.
        self.assertEqual((coder["price_aud"]["basis"], coder["price_aud"]["source"]), ("list price", "vercel"))
        self.assertAlmostEqual(coder["price_aud"]["input_per_1m"], 1.5 / 0.6979, places=3)
        cheapest = coder["price_aud"]["cheapest_available"]
        self.assertEqual((cheapest["gateway"], cheapest["input_usd_per_1m"]), ("openrouter", 0.3))
        self.assertEqual({p["gateway"] for p in coder["providers_global"]["providers"]}, {"vercel"})
        self.assertTrue(coder["spread"]["by_token_price"]["on_frontier"])
        self.assertEqual(sonnet["spread"]["by_token_price"]["dominated_by"], "alibaba/qwen3-coder")
        self.assertEqual(result["summary"]["smartest_open_model"]["id"], "alibaba/qwen3-coder")
        self.assertTrue(any("Artificial Analysis API not used" in w for w in result["report"]["warnings"]))

    def test_cost_per_task_is_left_empty_and_says_why(self):
        result = self.build(with_aa=True)
        self.assertTrue(all(m["cost_per_task_aud"] is None for m in result["models"]))
        self.assertTrue(all(m["spread"]["by_cost_per_task"] is None for m in result["models"]))
        point = next(p for p in result["points"] if p["field"] == "cost_per_task_aud")
        self.assertEqual(point["status"], "no_source")
        by_task = result["spread_map"]["by_cost_per_task"]
        self.assertEqual((by_task["status"], by_task["all_models"]["models"]), ("empty", 0))
        self.assertIn("Left empty rather than estimated", by_task["reason"])

    def test_hand_transcribed_cost_per_task(self):
        costs = [
            {"artificial_analysis_slug": "claude-4-5-sonnet-thinking", "chart_label": "Claude 4.5 Sonnet", "cost_per_task_usd": 5.46, "note": ""},
            {"artificial_analysis_slug": "gemini-4-argon", "chart_label": "Gemini 4 Argon (high)", "cost_per_task_usd": 1.99, "note": "x"},
            {"artificial_analysis_slug": "not-a-model", "chart_label": "?", "cost_per_task_usd": 1.0, "note": ""},
        ]
        result = self.build(with_aa=True, cost_per_task=costs)
        models = {m["id"]: m for m in result["models"]}
        sonnet = models["anthropic/claude-sonnet-4.5"]["cost_per_task_aud"]
        self.assertEqual((sonnet["usd"], sonnet["source"], sonnet["scope"]), (5.46, "hand-transcribed", "global"))
        self.assertAlmostEqual(sonnet["aud"], 5.46 / 0.6979, places=3)
        self.assertIsNone(models["alibaba/qwen3-coder"]["cost_per_task_aud"])
        self.assertEqual(next(p for p in result["points"] if p["field"] == "cost_per_task_aud")["status"], "hand-transcribed")
        self.assertTrue(any("not-a-model" in w for w in result["report"]["warnings"]))

        by_task = result["spread_map"]["by_cost_per_task"]
        self.assertEqual((by_task["role"], by_task["status"], by_task["all_models"]["models"]), ("main", "ok", 2))
        self.assertEqual(result["spread_map"]["by_token_price"]["role"], "secondary")
        # Argon is smarter and cheaper per task, but is on neither gateway.
        self.assertEqual(models["anthropic/claude-sonnet-4.5"]["spread"]["by_cost_per_task"]["dominated_by"], "aa:gemini-4-argon")
        self.assertEqual([p["id"] for p in by_task["available_models"]["frontier"]], ["anthropic/claude-sonnet-4.5"])
        self.assertEqual(by_task["all_models"]["frontier"][0]["intelligence_index"], 52.6)

    def test_api_cost_per_task_is_used_and_checked_against_the_hand_file(self):
        hand = [
            {"artificial_analysis_slug": "claude-4-5-sonnet-thinking", "chart_label": "", "cost_per_task_usd": 5.46, "note": ""},
            {"artificial_analysis_slug": "gemini-4-argon", "chart_label": "", "cost_per_task_usd": 2.50, "note": ""},
        ]
        # AA reports 0 where it has no figure (k2-horizon), and the weaker Sonnet run has its own cost.
        api = {"claude-4-5-sonnet-thinking": 5.4609, "claude-4-5-sonnet": 1.1, "gemini-4-argon": 1.9903, "k2-horizon": 0}
        result = self.build(with_aa=True, cost_per_task=hand, api_costs=api)
        models = {m["id"]: m for m in result["models"]}
        sonnet = models["anthropic/claude-sonnet-4.5"]["cost_per_task_aud"]
        self.assertEqual((sonnet["usd"], sonnet["source"]), (5.4609, "artificial_analysis_api"))
        self.assertEqual(models["aa:gemini-4-argon"]["cost_per_task_aud"]["usd"], 1.9903)
        self.assertIsNone(models["aa:k2-horizon"]["cost_per_task_aud"])
        self.assertEqual(next(p for p in result["points"] if p["field"] == "cost_per_task_aud")["status"], "phase_1")
        # 5.46 agrees with 5.4609 to the cent; 2.50 against 1.9903 does not.
        warnings = [w for w in result["report"]["warnings"] if "differs" in w]
        self.assertEqual(len(warnings), 1)
        self.assertIn("gemini-4-argon", warnings[0])

    def test_openrouter_discount_is_removed_from_the_list_price(self):
        # OpenRouter charges $2/$10 after 50% off; the list price is $4/$20. A flex tier is not "the model".
        endpoints = [
            {"provider_name": "OpenAI", "tag": "openai", "status": 0,
             "pricing": {"prompt": "0.000002", "completion": "0.00001", "discount": 0.5}},
            {"provider_name": "OpenAI", "tag": "openai/flex", "status": 0,
             "pricing": {"prompt": "0.000001", "completion": "0.000005", "discount": 0.5}},
            {"provider_name": "Azure", "tag": "azure", "status": 0,
             "pricing": {"prompt": "0.000004", "completion": "0.00002", "discount": 0}},
            {"provider_name": "Down", "tag": "down", "status": -2,
             "pricing": {"prompt": "0.0000001", "completion": "0.0000001", "discount": 0}},
        ]
        openrouter = {"id": "openai/gpt-5.6-sol", "pricing": {"prompt": "0.000002", "completion": "0.00001"}}
        price = snapshot._price(None, openrouter, None, snapshot._providers(None, endpoints), 1 / 0.6979)
        self.assertEqual(price["source"], "openrouter")
        self.assertAlmostEqual(price["input_per_1m"], 4 / 0.6979, places=3)
        self.assertEqual(price["by_source"]["openrouter"]["discount_removed"], 0.5)
        cheapest = price["cheapest_available"]
        self.assertEqual((cheapest["provider"], cheapest["input_usd_per_1m"], cheapest["discount"]), ("OpenAI", 2.0, 0.5))

    def test_quantized_deployments_are_reported_separately(self):
        def endpoint(provider, price, quantization):
            return {"provider_name": provider, "tag": provider, "status": 0, "quantization": quantization,
                    "pricing": {"prompt": str(price / 1e6), "completion": str(price / 1e6), "discount": 0}}
        endpoints = [endpoint("four-bit", 0.1, "fp4"), endpoint("nv", 0.2, "nvfp4"), endpoint("eight-bit", 0.3, "fp8"),
                     endpoint("unstated", 0.4, "unknown"), endpoint("full", 0.5, "bf16")]
        openrouter = {"id": "x/y", "pricing": {"prompt": "0.0000003", "completion": "0.0000003"}}
        price = snapshot._price(None, openrouter, None, snapshot._providers(None, endpoints), 1.0)
        self.assertEqual((price["cheapest_available"]["provider"], price["cheapest_available"]["quantization"]),
                         ("eight-bit", "fp8"))
        self.assertEqual((price["cheapest_quantized"]["provider"], price["cheapest_quantized"]["quantization"]),
                         ("four-bit", "fp4"))
        # A model with only unstated-precision providers has no quantized offer.
        price = snapshot._price(None, openrouter, None, snapshot._providers(None, endpoints[3:4]), 1.0)
        self.assertEqual((price["cheapest_available"]["provider"], price["cheapest_quantized"]), ("unstated", None))

    def test_providers_in_australia(self):
        vercel = [
            {"provider_name": "bedrock", "pricing": {"prompt": "0.000004", "completion": "0.00002"},
             "inference_regions": [
                 {"scope": "specific", "geo_region": "us", "provider_region": "us-east-1"},
                 {"scope": "specific", "geo_region": "au", "provider_region": "ap-southeast-2",
                  "pricing": {"prompt": "0.0000044", "completion": "0.000022",
                              "prompt_tiers": [{"cost": "0.0000044", "min": 0, "max": 200001}]}}]},
            {"provider_name": "anthropic", "pricing": {"prompt": "0.000004", "completion": "0.00002"}},
        ]
        openrouter = [
            {"provider_name": "Sydney Cloud", "tag": "sydney", "status": 0,
             "pricing": {"prompt": "0.000005", "completion": "0.000025"}},
            {"provider_name": "Sydney Cloud", "tag": "sydney/flex", "status": 0,
             "pricing": {"prompt": "0.000001", "completion": "0.000005"}},
            {"provider_name": "US Only", "tag": "us", "status": 0, "pricing": {"prompt": "0.000001", "completion": "0.000005"}},
        ]
        listings = {"Sydney Cloud": {"headquarters": "AU", "datacenters": ["AU", "US"]},
                    "US Only": {"headquarters": "US", "datacenters": ["US"]}}
        providers = snapshot._providers(vercel, openrouter, listings)
        self.assertEqual(providers[0]["inference_regions"], ["au", "us"])
        list_price = {"blended_3to1_per_1m": metrics.blended(4.0, 20.0)}
        australia = snapshot._australia(providers, list_price, 1.0)
        self.assertEqual(australia["scope"], "australia")
        # Bedrock's Sydney region at its own price, and the OpenRouter provider with an Australian datacenter; not flex.
        self.assertEqual([(d["provider"], d["region"]) for d in australia["providers"]],
                         [("bedrock", "ap-southeast-2"), ("Sydney Cloud", "AU")])
        self.assertTrue(australia["providers"][0]["tiered"])
        self.assertEqual((australia["cheapest"]["provider"], australia["cheapest"]["blended_aud_per_1m"]),
                         ("bedrock", metrics.blended(4.4, 22.0)))
        self.assertAlmostEqual(australia["vs_list_price"], 0.1)

        # Providers known but none in Australia: an empty answer. No provider data at all: unknown.
        none_here = snapshot._australia(snapshot._providers(vercel[1:], openrouter[2:], listings), list_price, 1.0)
        self.assertEqual((none_here["count"], none_here["cheapest"], none_here["vs_list_price"]), (0, None, None))
        self.assertIsNone(snapshot._australia([], list_price, 1.0))

    def test_australian_hosted_spread_map(self):
        result = self.build(with_aa=True)
        models = {m["id"]: m for m in result["models"]}
        coder = models["alibaba/qwen3-coder"]["providers_in_australia"]
        self.assertEqual((coder["count"], coder["providers"][0]["region"]), (1, "ap-southeast-2"))
        self.assertIsNone(models["anthropic/claude-sonnet-4.5"]["providers_in_australia"])
        self.assertEqual(next(p for p in result["points"] if p["point"] == 10)["status"], "phase_1")
        hosted = result["summary"]["hosted_in_australia"]
        self.assertEqual((hosted["scope"], hosted["models"]), ("australia", 1))
        self.assertEqual(hosted["models_by_intelligence"][0]["australian_providers"], ["alibaba (ap-southeast-2)"])
        by_price = result["spread_map"]["by_token_price"]
        self.assertEqual([p["id"] for p in by_price["australian_hosted_models"]["frontier"]], ["alibaba/qwen3-coder"])
        self.assertTrue(models["alibaba/qwen3-coder"]["spread"]["by_token_price"]["on_australian_hosted_frontier"])

    def test_value_for_money_has_an_intelligence_floor(self):
        models = {m["id"]: m for m in self.build(with_aa=True)["models"]}
        self.assertIsNotNone(models["anthropic/claude-sonnet-4.5"]["value_aud"])    # 30.0
        self.assertIsNone(models["alibaba/qwen3-coder"]["value_aud"])              # 25.0

    def test_with_artificial_analysis(self):
        result = self.build(with_aa=True)
        models = {m["id"]: m for m in result["models"]}

        sonnet = models["anthropic/claude-sonnet-4.5"]
        self.assertEqual(sonnet["intelligence"]["index"], 30.0)
        self.assertEqual(sonnet["intelligence"]["source"], "artificial_analysis_api")
        self.assertEqual(sonnet["ids"]["artificial_analysis"], "claude-4-5-sonnet-thinking")
        # 30.0 from the API against 20.7 in OpenRouter's copy is flagged for review.
        self.assertEqual(result["report"]["intelligence_disagreements"][0]["id"], "anthropic/claude-sonnet-4.5")
        self.assertEqual(result["report"]["warnings"], [])

        # A model only Artificial Analysis lists gets one row, for its best setting.
        argon = models["aa:gemini-4-argon"]
        self.assertNotIn("aa:gemini-4-argon-low", models)
        self.assertEqual((argon["on_gateways"], argon["open_weights"], argon["intelligence"]["index"]), (False, None, 52.6))
        self.assertEqual(argon["price_aud"]["source"], "artificial_analysis")
        # AA's 0 means "no price", not "free".
        self.assertIsNone(models["aa:k2-horizon"]["price_aud"])

        by_price = result["spread_map"]["by_token_price"]
        self.assertIn("aa:gemini-4-argon", [p["id"] for p in by_price["all_models"]["frontier"]])
        self.assertNotIn("aa:gemini-4-argon", [p["id"] for p in by_price["available_models"]["frontier"]])
        self.assertTrue(models["anthropic/claude-sonnet-4.5"]["spread"]["by_token_price"]["on_available_frontier"])


if __name__ == "__main__":
    unittest.main()
