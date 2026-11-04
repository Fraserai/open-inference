"""Match model names across providers and Artificial Analysis.

Every source spells models differently ("zai/glm-5.2", "GLM-5.2", "GLM 5.2 (Max)"), so
names are compared on a key: the sorted words of the name plus its numbers in order.
Sorting words absorbs reordering; keeping number order stops "4.5" matching "5.4".
Settings in brackets and words like "instruct" or "it" are dropped. Known spellings
that still don't line up go in ALIASES.
"""

import re

# Maker names are dropped too: sources disagree on whether "Meta", "NVIDIA" or "Google"
# is part of the model name.
NOISE_WORDS = {"instruct", "it", "chat", "pt", "v", "bf16", "fp8", "hf", "meta", "nvidia", "google"}
WORD_MAP = {"thinking": "reasoning"}

# Provider spelling (lower case, as written) -> the Artificial Analysis name.
ALIASES = {
    "llama-4-maverick-17b-128e-instruct": "Llama 4 Maverick",
    "llama-4-scout-17b-16e-instruct": "Llama 4 Scout",
    # SCX describes "Qwen3.8" as the 2.4T sparse MoE (~95B active).
    "qwen3.8": "Qwen3.8 2.4T A95B",
}


def key(name):
    if not name:
        return ((), ())
    alias = ALIASES.get(name.strip().lower())
    if alias:
        name = alias
    name = name.split("/")[-1]                       # drop "zai/" style prefixes
    name = re.sub(r"\([^)]*\)", " ", name)          # drop "(Max)", "(Reasoning)"
    text = name.lower().replace("+", " plus ")
    tokens = [WORD_MAP.get(t, t) for t in re.findall(r"[a-z]+|\d+", text)]
    words = tuple(sorted(t for t in tokens if t.isalpha() and t not in NOISE_WORDS))
    numbers = tuple(t for t in tokens if t.isdigit())
    return words, numbers


class ScoreIndex:
    """Look up a model's Artificial Analysis entry by any spelling of its name."""

    def __init__(self, models):
        self.by_key = {}
        for model in models:
            for name in (model.get("name"), model.get("aa_name")):
                k = key(name)
                if not k[0] and not k[1]:
                    continue
                current = self.by_key.get(k)
                if current is None or (model.get("score") or 0) > (current.get("score") or 0):
                    self.by_key[k] = model

    def find(self, name):
        return self.by_key.get(key(name))
