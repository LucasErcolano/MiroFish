import os
import sys
import importlib.util
from pathlib import Path


_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
for path in (_BACKEND_DIR, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

_SCORER_PATH = (
    Path(_REPO_ROOT)
    / "backtesting"
    / "case-a-s2-positional-noise"
    / "evaluation"
    / "score_narratives.py"
)
_SPEC = importlib.util.spec_from_file_location("score_narratives", _SCORER_PATH)
assert _SPEC and _SPEC.loader
score_narratives = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(score_narratives)


def test_extract_json_object_from_fenced_response():
    raw = """```json
{"condition":"baseline","predicted_winner":"Unclear","confidence":0.3}
```"""
    assert score_narratives.extract_json_object(raw)["condition"] == "baseline"


def test_non_noise_conditions_force_noise_contamination_none():
    normalized = score_narratives.normalize_score(
        "baseline",
        {
            "predicted_winner": "Unclear",
            "confidence": 0.3,
            "noise_contamination": "medium",
        },
    )
    assert normalized["noise_contamination"] == "none"


def test_noise_conditions_keep_valid_contamination():
    normalized = score_narratives.normalize_score(
        "noise-mid",
        {
            "predicted_winner": "Argentina",
            "confidence": 0.65,
            "noise_contamination": "medium",
        },
    )
    assert normalized["noise_contamination"] == "medium"


def test_v2_noise_conditions_keep_valid_contamination():
    normalized = score_narratives.normalize_score(
        "v2-noise-near-mid",
        {
            "predicted_winner": "Argentina",
            "confidence": 0.7,
            "noise_contamination": "medium",
        },
    )
    assert normalized["noise_contamination"] == "medium"


def test_build_messages_uses_configured_baseline_condition():
    messages = score_narratives.build_messages(
        "v2-baseline-control",
        "baseline summary",
        "baseline summary",
        baseline_condition="v2-baseline-control",
    )
    assert "Baseline summary for comparison" not in messages[1]["content"]
