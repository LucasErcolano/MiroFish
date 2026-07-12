from types import SimpleNamespace
from unittest.mock import patch

from app.services.oasis_profile_generator import OasisProfileGenerator


class _FakeCompletions:
    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents[min(len(self.calls) - 1, len(self.contents) - 1)]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason="stop",
                )
            ]
        )


def _generator(model_name, contents):
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)
    generator.model_name = model_name
    completions = _FakeCompletions(contents)
    generator.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return generator, completions


def _generate(generator):
    return generator._generate_profile_with_llm(
        entity_name="Alice",
        entity_type="Person",
        entity_summary="Alice summary",
        entity_attributes={},
        context="",
    )


def test_qwen_profile_generation_omits_json_object_constraint():
    generator, completions = _generator(
        "qwen/qwen3-8b",
        ['{"bio":"Analyst","persona":"Careful forecaster"}'],
    )

    result = _generate(generator)

    assert result["bio"] == "Analyst"
    assert "response_format" not in completions.calls[0]


def test_qwen_profile_generation_repairs_raw_newlines():
    generator, _ = _generator(
        "qwen/qwen3-8b",
        ['{"bio":"Analyst","persona":"Line one\nLine two"}'],
    )

    result = _generate(generator)

    assert result["bio"] == "Analyst"
    assert "Line one" in result["persona"]
    assert "Line two" in result["persona"]


def test_profile_generation_rejects_json_scalars_and_falls_back():
    generator, completions = _generator("qwen/qwen3-8b", ['"display_name"'])

    with patch("app.services.oasis_profile_generator.time.sleep", return_value=None):
        result = _generate(generator)

    assert isinstance(result, dict)
    assert result["bio"] == "Alice summary"
    assert len(completions.calls) == 3
