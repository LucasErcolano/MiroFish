# Report Agent Artifact-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate condition-isolated ReportAgent reports for Issue 19 from committed/local experiment artifacts and run them with Qwen, Gemma, and Llama.

**Architecture:** Add an explicit artifact-only mode to `ReportAgent` so benchmark reports can be grounded in a per-condition evidence bundle without calling shared graph/Zep tools. A backtesting runner will build one artifact context per V2 condition/model, invoke ReportAgent with unique report IDs, and copy compact outputs into the evaluation folder.

**Tech Stack:** Python 3.11, `uv`, existing `ReportAgent`, OpenAI-compatible LLM endpoints for OpenRouter and DeepInfra.

---

### Task 1: Artifact-Only ReportAgent Mode

**Files:**
- Modify: `backend/app/services/report_agent.py`
- Modify: `backend/app/services/report_agent_quality_guards.py`
- Test: `tests/test_report_agent_resilience.py`

- [ ] Add `artifact_context` and `artifact_only` constructor parameters.
- [ ] Add the artifact context to outline and section prompts.
- [ ] In artifact-only mode, disable tool descriptions and allow zero-tool validation only for this explicit path.
- [ ] Preserve existing default behavior: normal ReportAgent still requires real tool calls.
- [ ] Add tests proving artifact-only prompts include the condition context and never execute Zep tools.

### Task 2: Issue 19 ReportAgent Runner

**Files:**
- Create: `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/run_report_agent_from_artifacts.py`

- [ ] Load V2 Qwen condition summaries and DeepInfra Gemma/Llama condition summaries.
- [ ] Build a compact per-condition artifact context from summary markdown plus metrics/narrative score rows.
- [ ] Run ReportAgent with `artifact_only=True`, unique report IDs, and provider-specific model env.
- [ ] Copy `full_report.md`, `meta.json`, `outline.json`, and a compact run manifest to `evaluation_report_agent/<model>/<condition>/`.

### Task 3: Three-Model Verification

**Files:**
- Create or update: `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/README.md`
- Create or update: `backtesting/case-a-s2-positional-noise-v2/evaluation_report_agent/report_agent_manifest.csv`

- [ ] Run unit tests for ReportAgent artifact-only mode.
- [ ] Run the ReportAgent runner for Qwen/OpenRouter, Gemma/DeepInfra, and Llama/DeepInfra.
- [ ] Verify each model has all six V2 condition reports or document any hard provider failure.
- [ ] Update Issue 19 docs to distinguish ReportAgent evidence from the prior deterministic/evaluator scoring path.
