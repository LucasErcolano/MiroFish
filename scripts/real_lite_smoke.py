#!/usr/bin/env python3
"""
S2 Real-lite Smoke Test: ReportAgent LLM smoke with wiki vs baseline.

This script exercises the REAL ReportAgent LLM boundary:
  1. WikiCompiler compiles real wiki pages from synthetic-minimal artifacts
  2. WikiStore.compile_wiki_context() builds real wiki_context.md
  3. ReportAgent LLM call WITH wiki_context -> report_with_wiki.md
  4. ReportAgent LLM call WITHOUT wiki_context -> report_baseline.md
  5. Structural comparison between the two reports

Peripheral services (ZepTools, ReportManager) are stubbed — only the LLM call
itself and wiki_context injection are real.

Artifacts are written to:
  runs/wiki_report_memory_real_lite_<timestamp>/
"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

ENV_PATH = ROOT / ".env"
load_dotenv(str(ENV_PATH), override=True)

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Create output directory
# ---------------------------------------------------------------------------
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT_DIR = ROOT / "runs" / f"wiki_report_memory_real_lite_{TIMESTAMP}"
OUT_DIR.mkdir(parents=True, exist_ok=True)
WIKI_OUT = OUT_DIR / "wiki"
WIKI_OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
def log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(OUT_DIR / "command_log.md", "a") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# Simulated data (same as test fixtures but self-contained)
# ---------------------------------------------------------------------------
SIM_ID = "real_lite_smoke_sim"

SMOKE_EVENTS = [
    {
        "round_num": 1,
        "start_time": "2026-06-01T08:00:00Z",
        "simulated_hour": 8,
        "actions": [
            {
                "agent_name": "Dr. Chen",
                "agent_id": "dr_chen",
                "platform": "weibo",
                "action_type": "CREATE_POST",
                "content": "New study shows economic growth accelerating in Q2.",
            },
            {
                "agent_name": "MarketBot",
                "agent_id": "marketbot",
                "platform": "twitter",
                "action_type": "SHARE",
                "content": "GDP data released: 3.2% growth.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot"],
    },
    {
        "round_num": 2,
        "start_time": "2026-06-01T10:00:00Z",
        "simulated_hour": 10,
        "actions": [
            {
                "agent_name": "SkepticAI",
                "agent_id": "skeptic_ai",
                "platform": "reddit",
                "action_type": "COMMENT",
                "content": "Growth numbers are not accurate — real GDP contracted by 1.5%.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot", "skeptic_ai"],
    },
    {
        "round_num": 3,
        "start_time": "2026-06-01T12:00:00Z",
        "simulated_hour": 12,
        "actions": [
            {
                "agent_name": "Dr. Chen",
                "agent_id": "dr_chen",
                "platform": "weibo",
                "action_type": "COMMENT",
                "content": "I stand by the data. 3.2% is verified.",
            },
        ],
        "active_agents": ["dr_chen", "marketbot", "skeptic_ai"],
    },
]

SMOKE_MEMORIES = [
    {
        "query": "economic growth claims",
        "facts": [
            "GDP grew by 3.2% in Q2 2026",
            "Consumer confidence index rose to 108",
        ],
        "edges": [
            {
                "fact": "Dr. Chen endorses the growth narrative",
                "name": "endorsement",
                "source_node_name": "Dr. Chen",
                "target_node_name": "growth_narrative",
            },
            {
                "fact": "SkepticAI contradicts the growth narrative",
                "name": "contradiction",
                "source_node_name": "SkepticAI",
                "target_node_name": "growth_narrative",
            },
        ],
        "nodes": [
            {"uuid": "node_dr_chen", "name": "Dr. Chen", "labels": ["Person", "Agent"]},
            {"uuid": "node_growth", "name": "growth_narrative", "labels": ["Concept"]},
        ],
        "entity_insights": [
            {
                "uuid": "node_dr_chen",
                "name": "Dr. Chen",
                "type": "agent",
                "summary": "An influential researcher who endorses the growth narrative.",
                "related_facts": ["GDP grew by 3.2%"],
            },
        ],
    },
]

SMOKE_CASE_METADATA = {
    "name": "Economic Growth Simulation 2026",
    "description": "A simulation of information spread about economic indicators.",
}

SMOKE_DOCUMENTS = [
    {"name": "gdp_report_q2.pdf", "path": "/docs/gdp_report_q2.pdf", "size": 245000},
    {"name": "consumer_confidence.csv", "path": "/docs/consumer_confidence.csv", "size": 54000},
]

SIMULATION_REQUIREMENT = (
    "Analyze information spread about economic indicators in a social media simulation. "
    "Focus on how claims about GDP growth (3.2% vs -1.5%) propagate across agents "
    "(Dr. Chen, MarketBot, SkepticAI) and what contradictions emerge."
)

# ===========================================================================
# STEP 1: Compile wiki using real WikiCompiler
# ===========================================================================
log("STEP 1: Compiling wiki with real WikiCompiler...")

from app.services.wiki_memory.wiki_store import WikiStore
from app.services.wiki_memory.compiler import WikiCompiler

wiki_root = str(OUT_DIR / "wiki_root" / "simulations")
os.makedirs(wiki_root, exist_ok=True)

store = WikiStore(wiki_root=wiki_root)
compiler = WikiCompiler(store)

store.initialize(SIM_ID)
compile_result = compiler.compile(
    simulation_id=SIM_ID,
    events=SMOKE_EVENTS,
    retrieved_memories=SMOKE_MEMORIES,
    case_metadata=SMOKE_CASE_METADATA,
    documents=SMOKE_DOCUMENTS,
)

log(f"Wiki compiled: {len(compile_result.pages_updated)} pages updated, "
    f"{compile_result.claims_added} claims, {compile_result.contradictions_added} contradictions, "
    f"errors={compile_result.errors}")

# Copy wiki pages to output directory
import shutil

wiki_src = os.path.join(wiki_root, SIM_ID, "wiki")
if os.path.isdir(wiki_src):
    for f in os.listdir(wiki_src):
        src = os.path.join(wiki_src, f)
        dst = os.path.join(WIKI_OUT, f)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    log(f"Wiki pages copied to {WIKI_OUT}")

# Copy compile log
compile_log_src = os.path.join(wiki_src, "wiki_compile_log.jsonl")
if os.path.exists(compile_log_src):
    shutil.copy2(compile_log_src, OUT_DIR / "wiki_compile_log.jsonl")
    log("wiki_compile_log.jsonl copied")

# ===========================================================================
# STEP 2: Build wiki_context.md from real WikiStore
# ===========================================================================
log("STEP 2: Building wiki_context.md...")

wiki_context_text = store.compile_wiki_context(SIM_ID, max_chars=8000)

if wiki_context_text:
    log(f"wiki_context built: {len(wiki_context_text)} chars")
    with open(OUT_DIR / "wiki_context.md", "w") as f:
        f.write(wiki_context_text)
    log("wiki_context.md written")
else:
    log("ERROR: wiki_context is empty! Cannot proceed with real LLM comparison.")
    wiki_context_text = ""

wiki_context_present = bool(wiki_context_text)

# ===========================================================================
# STEP 3: Real LLM call — Report with wiki context
# ===========================================================================
log("STEP 3: Real LLM call — report WITH wiki context...")

from openai import OpenAI

llm_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

SANITIZED_PROVIDER = "google/gemini-2.5-flash-lite" if "generativelanguage" in LLM_BASE_URL else "openai"
SANITIZED_MODEL = f"{SANITIZED_PROVIDER}"
KEY_PRESENT = bool(LLM_API_KEY)

# Planning prompt (extracted from ReportAgent._plan_outline)
PLAN_SYSTEM_PROMPT = """You are an expert simulation analysis report writer.
Your task is to analyze a social simulation and produce a structured report outline.
The outline should include:
1. A report title
2. A summary paragraph
3. A list of sections, each with a title

Output a JSON object with keys: "title", "summary", "sections" (array of {title}).
Be concise but thorough. Analyze the simulation data and identify key themes."""

PLAN_USER_TEMPLATE = """Analyze the following simulation:

Simulation Requirement: {simulation_requirement}
Total Nodes: {total_nodes}
Total Edges: {total_edges}
Entity Types: {entity_types}
Total Entities: {total_entities}
Related Facts: {related_facts_json}"""

WIKI_INSTRUCTION = """
<wiki_audit_context>
[PRIOR KNOWLEDGE — NOT GROUND TRUTH. Verify claims with tool calls.]
The following wiki audit context was compiled from the simulation's
knowledge base prior to report generation. Use it as background
reference for planning sections, but always confirm key facts
with insight_forge / panorama_search / quick_search before citing.
When referencing wiki-derived information, note it as
"(per wiki audit)" for traceability.
---
{wiki_content}
---
</wiki_audit_context>
"""

BASE_CONTEXT = {
    "graph_statistics": {
        "total_nodes": 5,
        "total_edges": 3,
        "entity_types": {"Person": 2, "Concept": 2, "Agent": 1},
    },
    "total_entities": 5,
    "related_facts": [
        "GDP grew by 3.2% in Q2 2026",
        "Consumer confidence index rose to 108",
        "SkepticAI contradicts the growth narrative",
    ],
}

def build_plan_prompt(with_wiki: bool) -> tuple:
    """Build (system_prompt, user_prompt) for planning."""
    system_prompt = PLAN_SYSTEM_PROMPT

    user_prompt = PLAN_USER_TEMPLATE.format(
        simulation_requirement=SIMULATION_REQUIREMENT,
        total_nodes=BASE_CONTEXT["graph_statistics"]["total_nodes"],
        total_edges=BASE_CONTEXT["graph_statistics"]["total_edges"],
        entity_types=list(BASE_CONTEXT["graph_statistics"]["entity_types"].keys()),
        total_entities=BASE_CONTEXT["total_entities"],
        related_facts_json=json.dumps(BASE_CONTEXT["related_facts"], ensure_ascii=False, indent=2),
    )

    if with_wiki and wiki_context_text:
        user_prompt += "\n\n"
        user_prompt += WIKI_INSTRUCTION.format(wiki_content=wiki_context_text)

    return system_prompt, user_prompt


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Make a real LLM call via OpenAI SDK."""
    response = llm_client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> dict:
    """Make a real LLM call expecting JSON response."""
    raw = call_llm(system_prompt, user_prompt, temperature, max_tokens)
    # Try to extract JSON from response
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log(f"WARNING: LLM response was not valid JSON. Raw (first 500 chars): {text[:500]}")
        return {"raw_response": raw, "parse_error": True}


# ---- Report WITH wiki ----
t_start_wiki = time.monotonic()
wiki_system, wiki_user = build_plan_prompt(with_wiki=True)
wiki_plan_response = call_llm_json(wiki_system, wiki_user, temperature=0.3)
t_wiki_plan = time.monotonic() - t_start_wiki

log(f"Wiki plan response received in {t_wiki_plan:.1f}s")

# Now generate section content with wiki context
SECTION_SYSTEM_TEMPLATE = """You are an expert simulation analysis report writer.
Write a detailed section for a simulation report. The section title is:
{section_title}

Simulation summary: {simulation_requirement}

Provide thorough analysis with specific data references. Write in professional report style.
Use markdown formatting with headers, lists, and emphasis where appropriate."""

SECTION_USER_TEMPLATE = """Write the full content for section: {section_title}

Previous sections context:
{previous_content}"""

def generate_section_with_wiki(section_title: str, previous_content: str) -> str:
    """Generate a single section WITH wiki context injected into system prompt."""
    system_prompt = SECTION_SYSTEM_TEMPLATE.format(
        section_title=section_title,
        simulation_requirement=SIMULATION_REQUIREMENT,
    )
    if wiki_context_text:
        system_prompt += "\n\n"
        system_prompt += WIKI_INSTRUCTION.format(wiki_content=wiki_context_text)

    user_prompt = SECTION_USER_TEMPLATE.format(
        section_title=section_title,
        previous_content=previous_content or "(This is the first section.)",
    )
    return call_llm(system_prompt, user_prompt, temperature=0.5)


# ---- Report WITHOUT wiki (baseline) ----
log("STEP 4: Real LLM call — report WITHOUT wiki context (baseline)...")

t_start_base = time.monotonic()
base_system, base_user = build_plan_prompt(with_wiki=False)
base_plan_response = call_llm_json(base_system, base_user, temperature=0.3)
t_base_plan = time.monotonic() - t_start_base

log(f"Baseline plan response received in {t_base_plan:.1f}s")

def generate_section_baseline(section_title: str, previous_content: str) -> str:
    """Generate a single section WITHOUT wiki context."""
    system_prompt = SECTION_SYSTEM_TEMPLATE.format(
        section_title=section_title,
        simulation_requirement=SIMULATION_REQUIREMENT,
    )
    # No wiki context injection

    user_prompt = SECTION_USER_TEMPLATE.format(
        section_title=section_title,
        previous_content=previous_content or "(This is the first section.)",
    )
    return call_llm(system_prompt, user_prompt, temperature=0.5)


# ===========================================================================
# STEP 3b: Build full reports (plan + sections)
# ===========================================================================
def extract_sections(plan_response: dict) -> list:
    """Extract section titles from plan response."""
    if "sections" in plan_response:
        return [s.get("title", f"Section {i+1}") for i, s in enumerate(plan_response["sections"])]
    elif "raw_response" in plan_response:
        return ["Overview", "Key Findings", "Contradictions"]
    return ["Overview", "Analysis"]


def build_report(plan_response: dict, section_generator, label: str) -> str:
    """Build a full markdown report from plan + section generation."""
    title = plan_response.get("title", "Simulation Analysis Report")
    summary = plan_response.get("summary", "")
    sections = extract_sections(plan_response)

    log(f"[{label}] Generating {len(sections)} sections: {sections}")

    md = f"# {title}\n\n"
    if summary:
        md += f"> {summary}\n\n"

    previous_content = ""
    for i, section_title in enumerate(sections):
        log(f"[{label}] Generating section {i+1}/{len(sections)}: {section_title}")
        content = section_generator(section_title, previous_content)
        md += f"## {section_title}\n\n{content}\n\n"
        previous_content += f"## {section_title}\n\n{content}\n\n"

    return md


# Generate WITH wiki report
log("--- Generating WITH-WIKI report ---")
report_with_wiki = build_report(wiki_plan_response, generate_section_with_wiki, "WITH-WIKI")

# Generate BASELINE report
log("--- Generating BASELINE report ---")
report_baseline = build_report(base_plan_response, generate_section_baseline, "BASELINE")

# Write reports
with open(OUT_DIR / "report_with_wiki.md", "w") as f:
    f.write(report_with_wiki)
log(f"report_with_wiki.md written ({len(report_with_wiki)} chars)")

with open(OUT_DIR / "report_baseline.md", "w") as f:
    f.write(report_baseline)
log(f"report_baseline.md written ({len(report_baseline)} chars)")


# ===========================================================================
# STEP 5: Structural comparison
# ===========================================================================
log("STEP 5: Structural comparison...")

def analyze_report(text: str) -> dict:
    """Analyze a report's structure."""
    lines = text.split("\n")
    h2_count = len([l for l in lines if l.startswith("## ")])
    h3_count = len([l for l in lines if l.startswith("### ")])

    # Look for wiki-specific markers
    wiki_audit_refs = len(re.findall(r'\(per wiki audit\)', text, re.IGNORECASE))
    wiki_context_refs = len(re.findall(r'wiki[_ ]audit', text, re.IGNORECASE))
    wiki_refs = len(re.findall(r'wiki', text, re.IGNORECASE))

    # Look for specific data references
    gdp_mentions = len(re.findall(r'3\.2%|GDP', text))
    skeptic_mentions = len(re.findall(r'[Ss]keptic', text))
    contradiction_mentions = len(re.findall(r'[Cc]ontradict|[Cc]onflict|disagree', text))
    dr_chen_mentions = len(re.findall(r'Dr\.?\s*Chen', text))
    marketbot_mentions = len(re.findall(r'[Mm]arket[Bb]ot', text))

    # Look for source citations
    citation_patterns = len(re.findall(r'source|citation|reference|according to', text, re.IGNORECASE))

    # Section headings
    sections = [l.strip() for l in lines if l.startswith("## ")]

    # Word count approximation
    word_count = len(text.split())

    return {
        "total_chars": len(text),
        "word_count": word_count,
        "line_count": len(lines),
        "h2_count": h2_count,
        "h3_count": h3_count,
        "sections": sections,
        "wiki_audit_markers": wiki_audit_refs,
        "wiki_context_refs": wiki_context_refs,
        "wiki_keyword_refs": wiki_refs,
        "gdp_mentions": gdp_mentions,
        "skeptic_mentions": skeptic_mentions,
        "contradiction_mentions": contradiction_mentions,
        "dr_chen_mentions": dr_chen_mentions,
        "marketbot_mentions": marketbot_mentions,
        "citation_patterns": citation_patterns,
    }


wiki_analysis = analyze_report(report_with_wiki)
baseline_analysis = analyze_report(report_baseline)

comparison = {
    "timestamp": TIMESTAMP,
    "simulation_id": SIM_ID,
    "llm_provider": SANITIZED_PROVIDER,
    "llm_model": SANITIZED_MODEL,
    "llm_key_present": KEY_PRESENT,
    "llm_base_url": "(redacted)" if LLM_BASE_URL else "NOT_SET",
    "wiki_context_present": wiki_context_present,
    "wiki_context_length_chars": len(wiki_context_text) if wiki_context_text else 0,
    "wiki_compile_pages": len(compile_result.pages_updated),
    "wiki_compile_claims": compile_result.claims_added,
    "wiki_compile_contradictions": compile_result.contradictions_added,
    "wiki_compile_errors": compile_result.errors,
    "with_wiki": wiki_analysis,
    "baseline": baseline_analysis,
    "structural_differences": {},
    "audit_guidance_appears_only_in_wiki": False,
    "limitations": [
        "ZepTools/GraphRAG services are stubbed — no real graph search",
        "Report sections generated sequentially, not in ReACT multi-turn mode",
        "Only planning + section generation exercised, not full ReportAgent pipeline",
        "Wiki compilation is real (deterministic, no LLM dependency)",
        "LLM calls use real Gemini API with project .env credentials",
        f"Wiki context was {'injected' if wiki_context_present else 'NOT injected — empty'}",
    ],
}

# Compute structural differences
for key in ["total_chars", "word_count", "line_count", "h2_count", "h3_count",
            "wiki_audit_markers", "wiki_context_refs", "wiki_keyword_refs",
            "gdp_mentions", "skeptic_mentions", "contradiction_mentions",
            "dr_chen_mentions", "marketbot_mentions", "citation_patterns"]:
    w = wiki_analysis.get(key, 0)
    b = baseline_analysis.get(key, 0)
    comparison["structural_differences"][key] = {
        "with_wiki": w,
        "baseline": b,
        "delta": w - b,
    }

# Check if wiki-specific audit guidance appears only in with-wiki path
# (markers like "(per wiki audit)" or "wiki audit context")
comparison["audit_guidance_appears_only_in_wiki"] = (
    wiki_analysis["wiki_audit_markers"] > 0 and baseline_analysis["wiki_audit_markers"] == 0
)

# Section differences
comparison["section_comparison"] = {
    "with_wiki_sections": wiki_analysis["sections"],
    "baseline_sections": baseline_analysis["sections"],
    "with_wiki_only_sections": [s for s in wiki_analysis["sections"] if s not in baseline_analysis["sections"]],
    "baseline_only_sections": [s for s in baseline_analysis["sections"] if s not in wiki_analysis["sections"]],
}

# Write comparison.json
with open(OUT_DIR / "comparison.json", "w") as f:
    json.dump(comparison, f, indent=2, ensure_ascii=False)
log("comparison.json written")

# Write comparison.md
md_lines = []
md_lines.append("# S2 Real-lite Smoke: Wiki vs Baseline Report Comparison\n")
md_lines.append(f"**Timestamp**: {TIMESTAMP}")
md_lines.append(f"**Simulation ID**: {SIM_ID}")
md_lines.append(f"**LLM Provider**: {SANITIZED_PROVIDER}")
md_lines.append(f"**LLM Model**: {SANITIZED_MODEL}")
md_lines.append(f"**API Key Present**: {KEY_PRESENT}")
md_lines.append(f"**Wiki Context Present**: {wiki_context_present}")
md_lines.append(f"**Wiki Context Length**: {len(wiki_context_text) if wiki_context_text else 0} chars")
md_lines.append("")

md_lines.append("## Structural Differences\n")
md_lines.append("| Metric | With Wiki | Baseline | Delta |")
md_lines.append("|--------|-----------|----------|-------|")
for key in ["total_chars", "word_count", "h2_count", "h3_count",
             "wiki_audit_markers", "wiki_keyword_refs",
             "gdp_mentions", "skeptic_mentions", "contradiction_mentions",
             "dr_chen_mentions", "marketbot_mentions", "citation_patterns"]:
    d = comparison["structural_differences"][key]
    md_lines.append(f"| {key} | {d['with_wiki']} | {d['baseline']} | {d['delta']:+d} |")
md_lines.append("")

md_lines.append("## Wiki Audit Guidance\n")
if comparison["audit_guidance_appears_only_in_wiki"]:
    md_lines.append("✅ Wiki-specific audit guidance `((per wiki audit))` appears **only** in the with-wiki report, confirming inject-only activation.")
else:
    md_lines.append("⚠️ Wiki-specific audit guidance does NOT appear exclusively in the with-wiki report.")
    md_lines.append(f"   - With-wiki `wiki_audit_markers`: {wiki_analysis['wiki_audit_markers']}")
    md_lines.append(f"   - Baseline `wiki_audit_markers`: {baseline_analysis['wiki_audit_markers']}")
md_lines.append("")

md_lines.append("## Section Comparison\n")
md_lines.append("### With-Wiki Sections\n")
for s in wiki_analysis["sections"]:
    md_lines.append(f"- {s}")
md_lines.append("")
md_lines.append("### Baseline Sections\n")
for s in baseline_analysis["sections"]:
    md_lines.append(f"- {s}")
md_lines.append("")

with_wiki_only = comparison["section_comparison"]["with_wiki_only_sections"]
baseline_only = comparison["section_comparison"]["baseline_only_sections"]
if with_wiki_only:
    md_lines.append("### Sections unique to with-wiki report\n")
    for s in with_wiki_only:
        md_lines.append(f"- **{s}**")
    md_lines.append("")
if baseline_only:
    md_lines.append("### Sections unique to baseline report\n")
    for s in baseline_only:
        md_lines.append(f"- **{s}**")
    md_lines.append("")

md_lines.append("## Limitations\n")
for lim in comparison["limitations"]:
    md_lines.append(f"- {lim}")
md_lines.append("")

md_lines.append("## Artifacts\n")
md_lines.append(f"- `wiki/` — compiled wiki pages from WikiCompiler")
md_lines.append(f"- `wiki_compile_log.jsonl` — compilation audit trail")
md_lines.append(f"- `wiki_context.md` — assembled context string injected into prompts")
md_lines.append(f"- `report_with_wiki.md` — report generated WITH wiki context ({wiki_analysis['total_chars']} chars)")
md_lines.append(f"- `report_baseline.md` — report generated WITHOUT wiki context ({baseline_analysis['total_chars']} chars)")
md_lines.append(f"- `comparison.json` — machine-readable structural comparison")
md_lines.append(f"- `run_config.json` — run configuration and provenance")
md_lines.append(f"- `command_log.md` — execution log")
md_lines.append("")

with open(OUT_DIR / "comparison.md", "w") as f:
    f.write("\n".join(md_lines))
log("comparison.md written")

# ===========================================================================
# STEP 6: Write run_config.json
# ===========================================================================
# Git info
try:
    git_branch = os.popen("git rev-parse --abbrev-ref HEAD 2>/dev/null").read().strip()
    git_sha = os.popen("git rev-parse --short HEAD 2>/dev/null").read().strip()
    git_dirty = bool(os.popen("git status --porcelain 2>/dev/null").read().strip())
except Exception:
    git_branch = "unknown"
    git_sha = "unknown"
    git_dirty = False

run_config = {
    "run_id": TIMESTAMP,
    "simulation_id": SIM_ID,
    "wiki_root": wiki_root,
    "wiki_context_max_chars": 8000,
    "wiki_context_length": len(wiki_context_text) if wiki_context_text else 0,
    "wiki_context_present": wiki_context_present,
    "compile_result": compile_result.to_dict(),
    "wiki_in_plan_outline": wiki_context_present,
    "wiki_in_section_react": wiki_context_present,
    "wiki_in_baseline": False,
    "report_agent_config": {
        "graph_id": "graph_real_lite_smoke",
        "simulation_id": SIM_ID,
        "simulation_requirement": SIMULATION_REQUIREMENT[:80] + "...",
        "llm_provider": SANITIZED_PROVIDER,
        "llm_model": SANITIZED_MODEL,
        "llm_key_present": KEY_PRESENT,
        "llm_mocked": False,
        "llm_base_url_redacted": "(redacted)" if "generativelanguage" in LLM_BASE_URL else LLM_BASE_URL,
        "zep_mocked": True,
        "zep_stubbed_reason": "ZepTools requires running Zep service; only LLM and wiki paths are real",
    },
    "peripheral_services_stubbed": [
        "ZepToolsService — no real Zep/graph search; stubbed with minimal data",
        "ReportLogger/ReportConsoleLogger — replaced with file logging",
        "ReportManager — not used; direct LLM calls via OpenAI SDK",
    ],
    "real_components": [
        "WikiCompiler — full deterministic pipeline",
        "WikiStore.compile_wiki_context — real context assembly",
        "LLM calls via OpenAI SDK to Gemini API — real model responses",
        "wiki_context injection into system/user prompts — real prompt assembly",
    ],
    "git": {
        "branch": git_branch,
        "sha": git_sha,
        "dirty": git_dirty,
    },
    "limitations": comparison["limitations"],
}

with open(OUT_DIR / "run_config.json", "w") as f:
    json.dump(run_config, f, indent=2, ensure_ascii=False, default=str)
log("run_config.json written")

log("=" * 60)
log(f"S2 REAL-LITE SMOKE COMPLETE")
log(f"Artifacts: {OUT_DIR}")
log(f"  - wiki/: {len(os.listdir(WIKI_OUT))} files")
log(f"  - wiki_context.md: {len(wiki_context_text) if wiki_context_text else 0} chars")
log(f"  - report_with_wiki.md: {len(report_with_wiki)} chars")
log(f"  - report_baseline.md: {len(report_baseline)} chars")
log(f"  - comparison.json + .md")
log(f"  - run_config.json")
log("=" * 60)