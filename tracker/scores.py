"""Model scores (Artificial Analysis Intelligence Index) and open-weights flags.

With ARTIFICIAL_ANALYSIS_API_KEY set, scores are pulled live and saved to
data/scores/<date>.json. Without it, the most recent saved file is used and the report
says how old it is. Open-weights comes from OpenRouter (a Hugging Face weights repo
is listed) where it can be matched, otherwise from the saved file.
"""

import json

from . import http
from .names import ScoreIndex, key

AA_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def latest_saved(scores_dir):
    files = sorted(scores_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No saved scores in {scores_dir}")
    return json.loads(files[-1].read_text())


def from_aa_response(body, openrouter_models, previous, day):
    """Turn an AA API response into our scores document."""
    open_keys = {key(m.get("name", "")): True for m in openrouter_models if m.get("hugging_face_id")}
    open_keys.update({key(m["id"]): True for m in openrouter_models if m.get("hugging_face_id")})
    old = ScoreIndex(previous["models"]) if previous else None
    models = []
    for entry in body.get("data", []):
        score = (entry.get("evaluations") or {}).get("artificial_analysis_intelligence_index")
        if score is None:
            continue
        name = entry.get("name", "")
        open_weights = True if key(name) in open_keys else None
        if open_weights is None and old:
            match = old.find(name)
            open_weights = match.get("open_weights") if match else None
        models.append({"name": name, "aa_name": name,
                       "creator": (entry.get("model_creator") or {}).get("slug"),
                       "score": score, "open_weights": open_weights,
                       "release_date": entry.get("release_date")})
    return {"as_of": day, "source": "Artificial Analysis Intelligence Index, live API (artificialanalysis.ai)",
            "models": models}


def load(day, scores_dir, aa_key, openrouter_models, offline=False):
    """Returns (scores document, status dict)."""
    previous = None
    try:
        previous = latest_saved(scores_dir)
    except FileNotFoundError:
        pass
    if aa_key and not offline:
        try:
            body = http.get_json(AA_URL, headers={"x-api-key": aa_key})
            doc = from_aa_response(body, openrouter_models or [], previous, day)
            (scores_dir / f"{day}.json").write_text(json.dumps(doc, indent=1))
            return doc, {"status": "live", "as_of": day}
        except Exception as error:
            if previous is None:
                raise
            return previous, {"status": "fallback", "as_of": previous["as_of"],
                              "detail": f"Live pull failed: {error}"}
    if previous is None:
        raise FileNotFoundError("No scores available: set ARTIFICIAL_ANALYSIS_API_KEY")
    detail = "ARTIFICIAL_ANALYSIS_API_KEY not set" if not aa_key else "offline run"
    return previous, {"status": "fallback", "as_of": previous["as_of"], "detail": detail}
