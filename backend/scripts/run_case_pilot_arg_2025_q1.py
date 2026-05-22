#!/usr/bin/env python3
"""
Run an equivalent, auditable PILOT-ARG-2025-Q1 prediction using the current
MiroFish repository when the fork CLI command `mirofish run` is unavailable.

This is intentionally conservative:
- no web access;
- no persistent memory;
- no answer_key_post_x reads;
- local pre-cutoff files only;
- raw output is saved unedited;
- deviations from the CLI/OASIS path are written to artifacts.

It uses only the Python standard library plus the system `pdftotext` command if
available. LLM calls are made directly against an OpenAI-compatible HTTP API
using LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME, matching the backend config
style without requiring a full backend dependency sync.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

FORBIDDEN_PATTERNS = [
    r"40[\.,]7",
    r"40[\.,]84",
    r"31[\.,]5",
    r"Reuters\s+2025-10",
    r"octubre\s+2025\s+gan",
    r"legislativas\s+de\s+octubre\s+de\s+2025\s+con",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path, max_chars: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + f"\n\n[TRUNCATED at {max_chars} chars from {len(text)} chars]"
    return text


def extract_pdf_text(path: Path, max_chars: int) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return f"[PDF extraction skipped: pdftotext not available for {path.name}]"
    proc = subprocess.run(
        [pdftotext, "-layout", str(path), "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=60,
    )
    if proc.returncode != 0:
        return f"[PDF extraction failed for {path.name}: {proc.stderr.strip()}]"
    text = proc.stdout
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[TRUNCATED at {max_chars} chars from extracted PDF]"
    return text


def extract_source_text(case_dir: Path, local_path: str, max_chars: int) -> str:
    path = case_dir / local_path
    if not path.exists():
        return f"[missing source file: {local_path}]"
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path, max_chars)
    if suffix in {".md", ".txt", ".html", ".htm", ".json", ".csv"}:
        return read_text(path, max_chars=max_chars)
    return f"[unsupported source extension {suffix}: {local_path}]"


def load_manifest(case_dir: Path) -> List[Dict[str, str]]:
    manifest_path = case_dir / "input_pack_pre_x" / "manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def validate_pre_cutoff(case_dir: Path, rows: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    cutoff = "2025-01-31"
    for row in rows:
        sid = row.get("source_id", "<missing>")
        if row.get("allowed_before_x", "").lower() != "true":
            errors.append(f"{sid}: allowed_before_x is not true")
        date = row.get("published_date", "")
        if date and len(date) >= 10 and date[:10] > cutoff:
            errors.append(f"{sid}: published_date {date} is after cutoff {cutoff}")
        local = row.get("local_path", "")
        path = case_dir / local
        if not path.exists():
            errors.append(f"{sid}: missing local file {local}")
        elif row.get("sha256") and sha256_file(path) != row.get("sha256"):
            errors.append(f"{sid}: sha256 mismatch for {local}")

    scan_targets = [case_dir / "input_pack_pre_x" / "seed_bundle.md"]
    scan_targets += list((case_dir / "input_pack_pre_x" / "excerpts").glob("*.md"))
    for path in scan_targets:
        if not path.exists():
            continue
        text = read_text(path)
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(f"forbidden pattern {pattern!r} in {path.relative_to(case_dir)}")
    return not errors, errors


def build_input_packet(case_dir: Path, source_chars: int) -> str:
    rows = load_manifest(case_dir)
    seed = read_text(case_dir / "input_pack_pre_x" / "seed_bundle.md")
    excerpts_dir = case_dir / "input_pack_pre_x" / "excerpts"
    parts = [
        "# Local pre-cutoff input packet",
        "Cutoff: 2025-01-31.",
        "The following content is compiled only from input_pack_pre_x.",
        "Do not use answer_key_post_x or external knowledge.",
        "",
        "## Seed bundle",
        seed,
        "",
        "## Source manifest",
    ]
    for row in rows:
        parts.append(json.dumps(row, ensure_ascii=False))
    parts.append("\n## Source excerpts")
    for row in rows:
        sid = row["source_id"]
        excerpt_path = excerpts_dir / f"{sid}.md"
        if excerpt_path.exists():
            parts.append(f"\n### {sid} excerpt\n{read_text(excerpt_path)}")
    parts.append("\n## Original local sources, extracted/truncated")
    for row in rows:
        sid = row["source_id"]
        title = row.get("title", "")
        local = row.get("local_path", "")
        extracted = extract_source_text(case_dir, local, source_chars)
        parts.append(f"\n### {sid} — {title}\nLocal path: {local}\n\n{extracted}")
    return "\n".join(parts)


def openai_compatible_chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    top_p: float,
    seed: int,
    max_tokens: int,
) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    # Gemini's OpenAI-compatible endpoint rejects the OpenAI `seed` field.
    # Keep the seed in run_config/verdict for auditability, but omit it from
    # Gemini HTTP payloads and document the unsupported parameter.
    if "generativelanguage.googleapis.com" not in base_url:
        payload["seed"] = seed
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {endpoint}: {body[:4000]}") from e
    parsed = json.loads(raw)
    return parsed["choices"][0]["message"]["content"]


def write_json(path: Path, obj: Dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-dir", default="cases/PILOT-ARG-2025-Q1")
    ap.add_argument("--num-runs", type=int, default=3)
    ap.add_argument("--source-chars", type=int, default=20000)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=20250131)
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL_NAME", "gemma-4-31b-it"))
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"))
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    case_dir = Path(args.case_dir)
    if not case_dir.is_absolute():
        case_dir = repo_root / case_dir
    output_dir = case_dir / "model_output_raw"
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    rows = load_manifest(case_dir)
    valid, validation_errors = validate_pre_cutoff(case_dir, rows)

    prompt = read_text(case_dir / "prompt_frozen" / "prompt.md")
    constraints = read_text(case_dir / "prompt_frozen" / "system_constraints.md")
    input_packet = build_input_packet(case_dir, args.source_chars)

    adapted_config = {
        "run_mode": "adapted_repo_direct_llm_equivalent",
        "case_id": "PILOT-ARG-2025-Q1",
        "started_at": started_at,
        "repo_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stdout=subprocess.PIPE).stdout.strip(),
        "model": args.model,
        "base_url": args.base_url,
        "knowledge_cutoff_claim": "2025-01",
        "web_access": False,
        "rag_external": False,
        "memory_persistent": False,
        "clear_previous_memory": True,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "seed": args.seed,
        "num_runs": args.num_runs,
        "platform_mode": "direct_llm_single_packet_logged",
        "output_format": "markdown_plus_json",
        "require_citations_to_input_ids": True,
        "forbid_post_cutoff_facts": True,
        "deviations_from_requested_mirofish_cli": [
            "No `mirofish` CLI is present in this repository/PATH.",
            "No OASIS Twitter/Reddit social simulation is executed by this adapted runner.",
            "No Zep/Graphiti memory graph is built or queried.",
            "All evidence is passed as one local pre-cutoff packet to an OpenAI-compatible chat completion endpoint.",
            "This runner is an auditable fallback, not a claimed equivalent of the full interactive MiroFish UI workflow."
        ],
        "unsupported_or_not_used_parameters": {
            "num_agents": "not applicable in direct LLM fallback",
            "num_rounds": "not applicable in direct LLM fallback",
            "social_interaction_simulation": "not executed",
            "persistent_memory_clear": "not needed because no persistent memory used",
            "seed_http_parameter": "omitted for Gemini OpenAI-compatible endpoint because Google rejects unknown field seed"
        },
        "input_packet_sha256": sha256_text(input_packet),
        "prompt_sha256": sha256_text(prompt),
        "validation_status": "PASS" if valid else "BLOCKED",
        "validation_errors": validation_errors,
    }
    write_json(output_dir / "adapted_run_config.json", adapted_config)
    (artifacts_dir / "adapted_input_packet.md").write_text(input_packet, encoding="utf-8")

    if not valid:
        msg = "BLOCKED: pre-cutoff validation failed.\n" + "\n".join(validation_errors)
        (output_dir / "mirofish_report_raw.md").write_text(msg, encoding="utf-8")
        write_json(output_dir / "verdict_raw.json", {"status": "BLOCKED", "reason": "pre_cutoff_validation_failed", "errors": validation_errors, "is_model_output": False})
        print(msg)
        return 2

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        msg = "BLOCKED: LLM_API_KEY is not configured; adapted repo runner cannot call the OpenAI-compatible backend."
        (output_dir / "mirofish_report_raw.md").write_text("# Adapted MiroFish raw report\n\n" + msg + "\n", encoding="utf-8")
        write_json(output_dir / "verdict_raw.json", {"status": "BLOCKED", "reason": "LLM_API_KEY not configured", "is_model_output": False, "adapted_runner": True})
        print(msg)
        return 3

    system_message = (
        constraints
        + "\n\nYou are running an auditable pre-cutoff prediction case. "
        + "Never use post-2025-01-31 facts. Cite source_id values from the packet."
    )
    user_message = (
        input_packet
        + "\n\n# Frozen prompt\n"
        + prompt
    )

    run_outputs = []
    for i in range(1, args.num_runs + 1):
        run_seed = args.seed + i - 1
        print(f"Starting adapted run {i}/{args.num_runs} seed={run_seed} model={args.model}", flush=True)
        content = openai_compatible_chat(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=args.temperature,
            top_p=args.top_p,
            seed=run_seed,
            max_tokens=args.max_tokens,
        )
        run_path = artifacts_dir / f"adapted_run_{i}_raw.md"
        run_path.write_text(content, encoding="utf-8")
        run_outputs.append({"run_index": i, "seed": run_seed, "path": str(run_path.relative_to(case_dir)), "sha256": sha256_file(run_path), "content": content})
        time.sleep(1)

    combined = ["# Adapted MiroFish raw report", "", "This is raw model output from the adapted repository runner. Do not edit before evaluation.", ""]
    for item in run_outputs:
        combined.append(f"\n---\n\n## Run {item['run_index']} — seed {item['seed']} — sha256 {item['sha256']}\n")
        combined.append(item["content"])
    combined_text = "\n".join(combined)
    raw_path = output_dir / "mirofish_report_raw.md"
    raw_path.write_text(combined_text, encoding="utf-8")

    verdict = {
        "status": "COMPLETED_ADAPTED_REPO_RUN",
        "is_model_output": True,
        "adapted_runner": True,
        "num_runs": args.num_runs,
        "model": args.model,
        "raw_report": str(raw_path.relative_to(case_dir)),
        "raw_report_sha256": sha256_file(raw_path),
        "runs": [{k: v for k, v in item.items() if k != "content"} for item in run_outputs],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_dir / "verdict_raw.json", verdict)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
