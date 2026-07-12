from app.services.report_agent_quality_guards import parse_tool_calls


def test_parse_tool_call_fenced_json():
    response = """I will verify this with a tool.

```tool_call
{"name": "quick_search", "parameters": {"query": "duplicate records Marta Alvarez", "limit": 5}}
```
"""

    calls = parse_tool_calls(
        response,
        {"insight_forge", "panorama_search", "quick_search", "interview_agents"},
    )

    assert calls == [
        {
            "name": "quick_search",
            "parameters": {"query": "duplicate records Marta Alvarez", "limit": 5},
        }
    ]
