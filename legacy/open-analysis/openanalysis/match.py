"""Work out which entries in each source are the same model.

No source shares ids with another ("anthropic/claude-sonnet-4.5" on the gateways is
"claude-4-5-sonnet" on Artificial Analysis), so models are compared on a normalised
key: creator, the sorted words of the name, and its version numbers in order.
Sorting words absorbs reordering; keeping number order stops gpt-5.4 matching gpt-4.5.
"""

import re
from collections import defaultdict

CREATOR_ALIASES = {
    "qwen": "alibaba",
    "meta-llama": "meta",
    "mistralai": "mistral",
    "x-ai": "xai",
    "spacexai": "xai",
    "z-ai": "zai",
    "bytedance-seed": "bytedance",
    "aws": "amazon",
}

# Dropped only in the second, relaxed pass.
NOISE_WORDS = {"instruct", "it", "preview"}


def norm_creator(creator):
    creator = (creator or "").lower().lstrip("~")
    return CREATOR_ALIASES.get(creator, creator)


def name_key(text):
    text = text.lower().replace("+", " plus ")      # "Command A+" is not "Command A"
    tokens = ["reasoning" if t == "thinking" else t for t in re.findall(r"[a-z]+|\d+", text)]
    words = tuple(sorted(t for t in tokens if t.isalpha()))
    numbers = tuple(t for t in tokens if t.isdigit())
    return words, numbers


def relax(key):
    """Drop release-stage words and date stamps (2512, 20260420) from a key."""
    words, numbers = key
    return (tuple(w for w in words if w not in NOISE_WORDS),
            tuple(n for n in numbers if len(n) < 4))


def gateway_key(model_id):
    creator, _, slug = model_id.partition("/")
    return (norm_creator(creator),) + name_key(slug)


def join_gateways(vercel_models, openrouter_models, aliases):
    """Pair Vercel and OpenRouter entries. Returns rows of {vercel, openrouter, match}."""
    vercel = {m["id"]: m for m in vercel_models}
    openrouter = {m["id"]: m for m in openrouter_models}
    rows = []

    def pair(vercel_id, openrouter_id, how):
        rows.append({"vercel": vercel.pop(vercel_id), "openrouter": openrouter.pop(openrouter_id), "match": how})

    for vercel_id, openrouter_id in aliases.items():
        if vercel_id in vercel and openrouter_id in openrouter:
            pair(vercel_id, openrouter_id, "override")

    def pass_(key_of, how):
        groups = defaultdict(lambda: ([], []))
        for model_id in vercel:
            groups[key_of(model_id)][0].append(model_id)
        for model_id in openrouter:
            groups[key_of(model_id)][1].append(model_id)
        # Only pair when the key is unambiguous on both sides.
        for vercel_ids, openrouter_ids in groups.values():
            if len(vercel_ids) == 1 and len(openrouter_ids) == 1:
                pair(vercel_ids[0], openrouter_ids[0], how)

    pass_(gateway_key, "exact")
    pass_(lambda i: (gateway_key(i)[0],) + relax(gateway_key(i)[1:]), "relaxed")

    rows += [{"vercel": m, "openrouter": None, "match": "vercel_only"} for m in vercel.values()]
    rows += [{"vercel": None, "openrouter": m, "match": "openrouter_only"} for m in openrouter.values()]
    return rows


# Bracketed words that describe how a model was run, not which model it is.
EFFORT_WORDS = {"max", "xhigh", "high", "medium", "low", "minimal", "reasoning", "thinking", "non", "adaptive"}


def intelligence(aa_model):
    return (aa_model.get("evaluations") or {}).get("artificial_analysis_intelligence_index")


def _is_effort(segment):
    words = re.findall(r"[a-z]+", segment.lower())
    return "fallback" in words or (bool(words) and all(w in EFFORT_WORDS for w in words))


def model_name(aa_name):
    """Drop run settings from an AA name: 'Claude Opus 5.5 (Max, Default Fallback)' -> 'Claude Opus 5.5'.

    Brackets that identify a different release are kept: 'Qwen3.8 Max (0902)', 'GPT-4o (Aug '24)'.
    """
    def keep(match):
        return " " + " ".join(seg for seg in match.group(1).split(",") if not _is_effort(seg)) + " "

    return re.sub(r"\(([^)]*)\)", keep, aa_name)


def best(aa_models):
    scored = [m for m in aa_models if intelligence(m) is not None]
    return max(scored, key=intelligence) if scored else aa_models[0]


class ArtificialAnalysisIndex:
    """Look up Artificial Analysis entries for a gateway model.

    AA lists each reasoning setting of a model as its own entry, "GPT-5 mini (High)",
    "GPT-5 mini (Medium)", and its charts show the best one. So entries are grouped
    by model name and the highest-scoring entry of the group represents the model.
    AA slugs are not used to pick within a group: the bare slug is sometimes the
    weakest setting ("claude-opus-4-5" is the non-reasoning run).
    """

    def __init__(self, models):
        self.by_slug = {m["slug"]: m for m in models}
        self.groups = defaultdict(list)       # (creator, model name) -> its entries
        # (label, table, key of an AA entry, transform applied to the gateway model's key)
        self._tiers = [
            ("name", defaultdict(list), lambda m: name_key(model_name(m["name"])), lambda key: key),
            # A gateway id that names the setting itself: grok-4.1-fast-reasoning.
            ("name_with_setting", defaultdict(list), lambda m: name_key(m["name"]), lambda key: key),
            # Last resort on names: ignore brackets, date stamps and words like "preview",
            # so every dated release of a model collapses together and the best one wins.
            ("name_relaxed", defaultdict(list),
             lambda m: relax(name_key(re.sub(r"\([^)]*\)", " ", m["name"]))), relax),
        ]
        self._slug = defaultdict(list)
        self._by_creator = defaultdict(list)
        for model in models:
            creator = self.creator(model)
            self._by_creator[creator].append(model)
            self.groups[self.group_of(model)].append(model)
            for _, table, key_of, _ in self._tiers:
                table[(creator,) + key_of(model)].append(model)
                table[key_of(model)].append(model)
            self._slug[(creator,) + name_key(model["slug"])].append(model)

    @staticmethod
    def creator(model):
        return norm_creator((model.get("model_creator") or {}).get("slug"))

    def group_of(self, model):
        return (self.creator(model),) + name_key(model_name(model["name"]))

    def lookup(self, creator, slugs, names=(), pinned_slug=None):
        """Find a gateway model by its id slugs, then by its display names.

        Returns (model, how, entries_considered) or (None, None, 0).
        """
        if pinned_slug and pinned_slug in self.by_slug:
            return self.by_slug[pinned_slug], "override", 1
        creator = norm_creator(creator)
        slug_keys = {name_key(slug) for slug in slugs if slug}
        name_keys = {name_key(name) for name in names if name} - slug_keys
        for with_creator in (True, False):
            for keys, from_display_name in ((slug_keys, False), (name_keys, True)):
                for how, table, _, transform in self._tiers:
                    found = {}
                    for key in {transform(key) for key in keys}:
                        for model in table.get((creator,) + key if with_creator else key, []):
                            if not from_display_name or self._consistent(model, slug_keys):
                                found[model["id"]] = model
                    # Without a creator to anchor on, only trust a name that one creator owns.
                    if not found or (not with_creator and len({self.creator(m) for m in found.values()}) > 1):
                        continue
                    return best(list(found.values())), how if with_creator else how + "_any_creator", len(found)
        return None, None, 0

    @staticmethod
    def _consistent(model, slug_keys):
        """Guard for display names, which can be wrong where an id cannot.

        One gateway shows "GPT 5.2" for gpt-5.2-pro. A match made on the display
        name stands only if the AA name contains every word of the id.
        """
        words = set(name_key(model["name"])[0])
        return any(set(key[0]) <= words for key in slug_keys)

    def lookup_by_score(self, creator, texts, score):
        """Pick out the dated release that a known score belongs to.

        A gateway id like deepseek-v4-pro does not say which of AA's dated releases
        (0424, 0813) it is. OpenRouter's copy of the AA score does: the release with
        the same name, date stamps aside, and the same score.
        """
        keys = {relax(name_key(text)) for text in texts if text}
        found = [m for m in self._by_creator[norm_creator(creator)]
                 if intelligence(m) is not None and abs(intelligence(m) - score) <= 0.05
                 and relax(name_key(model_name(m["name"]))) in keys]
        return (found[0], "openrouter_score", len(found)) if found else (None, None, 0)

    def lookup_slug(self, creator, texts):
        """Match on the AA slug. Weaker than names; used only when nothing else is known."""
        creator = norm_creator(creator)
        found = {m["id"]: m for text in texts if text for m in self._slug.get((creator,) + name_key(text), [])}
        return (best(list(found.values())), "slug", len(found)) if found else (None, None, 0)
