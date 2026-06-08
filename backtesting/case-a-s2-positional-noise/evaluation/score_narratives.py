"""Score S2 Issue 19 condition summaries with a hosted evaluator model.

The script uses only deterministic condition summaries as input. It does not
touch simulation state, does not rerun MiroFish, and does not call ReportAgent.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


CONDITIONS = [
    "baseline",
    "signal-early",
    "signal-mid",
    "signal-late",
    "noise-early",
    "noise-mid",
    "noise-late",
]

VALID_WINNERS = {"Argentina", "Colombia", "Unclear"}
VALID_CONTAMINATION = {"none", "low", "medium", "high"}


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def ensure_backend_imports(repo_root: Path) -> None:
    backend_dir = repo_root / "backend"
    for path in (str(repo_root), str(backend_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)


def configure_llm_env() -> None:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = openrouter_key
    if os.environ.get("LLM_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["LLM_API_KEY"]
    os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    os.environ.setdefault("LLM_MODEL_NAME", "qwen/qwen3-8b")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def strip_json_fences(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_json_fences(text)
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start < 0:
        raise ValueError(f"No JSON object found in response: {cleaned[:300]}")

    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(cleaned[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                return json.loads(candidate, strict=False)

    raise ValueError(f"Could not isolate valid JSON object: {cleaned[:300]}")


def normalize_score(condition: str, raw: dict[str, Any]) -> dict[str, Any]:
    winner = str(raw.get("predicted_winner", "Unclear")).strip()
    if winner not in VALID_WINNERS:
        winner = "Unclear"

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    evidence = raw.get("main_evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    if not isinstance(evidence, list):
        evidence = []
    evidence = [str(item).strip() for item in evidence if str(item).strip()][:5]

    contamination = str(raw.get("noise_contamination", "none")).strip().lower()
    if contamination not in VALID_CONTAMINATION:
        contamination = "none"
    if "noise" not in condition:
        contamination = "none"

    return {
        "condition": condition,
        "predicted_winner": winner,
        "confidence": round(confidence, 2),
        "main_evidence": evidence,
        "used_injected_document": bool(raw.get("used_injected_document", False)),
        "noise_contamination": contamination,
        "difference_vs_baseline": str(raw.get("difference_vs_baseline", "")).strip(),
        "notes": str(raw.get("notes", "")).strip(),
    }


def build_messages(
    condition: str,
    summary: str,
    baseline_summary: str | None,
    baseline_condition: str = "baseline",
) -> list[dict[str, str]]:
    system = (
        "You are evaluating a Reddit simulation for a sports prediction experiment. "
        "Use only the supplied condition summary. Do not use real-world final match "
        "knowledge unless it appears in the supplied summary. Extract the prediction "
        "implied by the simulated discussion and identify whether injected signal or "
        "noise changed the narrative. Return strict JSON only. Do not invent "
        "statistics, probabilities, scores, or rates. If you cite a number, it "
        "must appear exactly in the supplied summaries."
    )

    baseline_block = ""
    if condition != baseline_condition and baseline_summary:
        baseline_block = (
            "\n\nBaseline summary for comparison:\n"
            "```markdown\n"
            f"{baseline_summary}\n"
            "```\n"
        )

    user = (
        f"Condition: {condition}\n"
        f"{baseline_block}\n"
        "Condition summary:\n"
        "```markdown\n"
        f"{summary}\n"
        "```\n\n"
        "Return strict JSON with exactly these keys:\n"
        "{\n"
        '  "condition": "' + condition + '",\n'
        '  "predicted_winner": "Argentina | Colombia | Unclear",\n'
        '  "confidence": 0.0,\n'
        '  "main_evidence": ["short evidence item 1", "short evidence item 2", "short evidence item 3"],\n'
        '  "used_injected_document": true,\n'
        '  "noise_contamination": "none | low | medium | high",\n'
        '  "difference_vs_baseline": "short comparison if baseline is known, otherwise empty",\n'
        '  "notes": "short note about ambiguity or failure modes"\n'
        "}\n"
        "Rules: confidence is 0..1; use Unclear for unstable winner; "
        "do not invent statistics or probabilities; cite only numbers present in the supplied summaries; "
        "mark used_injected_document true only when the injected post influenced later discussion or top-discussed content; "
        "for noise runs, contamination is higher when ticketing, travel, celebrity/media attention, or non-match evidence affects rationale."
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def score_with_llm(
    condition: str,
    summary: str,
    baseline_summary: str | None,
    max_tokens: int,
    baseline_condition: str = "baseline",
) -> tuple[str, dict[str, Any]]:
    from app.utils.llm_client import LLMClient

    client = LLMClient()
    raw_text = client.chat(
        build_messages(
            condition,
            summary,
            baseline_summary,
            baseline_condition=baseline_condition,
        ),
        temperature=0.1,
        max_tokens=max_tokens,
    )
    raw_json = extract_json_object(raw_text)
    return raw_text, normalize_score(condition, raw_json)


def write_csv(scores: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "condition",
        "predicted_winner",
        "confidence",
        "used_injected_document",
        "noise_contamination",
        "main_evidence",
        "difference_vs_baseline",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for score in scores:
            writer.writerow(
                {
                    **score,
                    "main_evidence": " | ".join(score["main_evidence"]),
                }
            )


def write_markdown(scores: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Narrative Scores",
        "",
        "Generated from deterministic condition summaries using the configured evaluator model.",
        "",
        "| condition | predicted_winner | confidence | used_injected_document | noise_contamination |",
        "|---|---|---:|---|---|",
    ]
    for score in scores:
        lines.append(
            "| {condition} | {predicted_winner} | {confidence:.2f} | {used_injected_document} | {noise_contamination} |".format(
                **score
            )
        )

    lines.append("")
    lines.append("## Evidence")
    for score in scores:
        lines.extend(
            [
                "",
                f"### {score['condition']}",
                "",
                f"- Predicted winner: `{score['predicted_winner']}`",
                f"- Confidence: `{score['confidence']:.2f}`",
                f"- Used injected document: `{score['used_injected_document']}`",
                f"- Noise contamination: `{score['noise_contamination']}`",
                f"- Difference vs baseline: {score['difference_vs_baseline'] or 'n/a'}",
                f"- Notes: {score['notes'] or 'n/a'}",
                "",
                "Main evidence:",
            ]
        )
        for item in score["main_evidence"]:
            lines.append(f"- {item}")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary-dir",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/condition_summaries"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/narrative_scores.csv"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/narrative_scores.md"),
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/narrative_score_raw"),
    )
    parser.add_argument("--max-tokens", type=int, default=1400)
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help="Rebuild CSV/Markdown from existing raw .txt outputs without calling the LLM.",
    )
    parser.add_argument(
        "--conditions",
        default=",".join(CONDITIONS),
        help="Comma-separated condition names to score.",
    )
    parser.add_argument(
        "--baseline-condition",
        default="baseline",
        help="Condition to use as baseline comparison.",
    )
    return parser.parse_args()


def repo_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    ensure_backend_imports(repo_root)
    configure_llm_env()

    args.summary_dir = repo_path(repo_root, args.summary_dir)
    args.output_csv = repo_path(repo_root, args.output_csv)
    args.output_md = repo_path(repo_root, args.output_md)
    args.raw_dir = repo_path(repo_root, args.raw_dir)

    conditions = [part.strip() for part in args.conditions.split(",") if part.strip()]
    if not conditions:
        raise ValueError("No conditions provided")
    if args.baseline_condition not in conditions:
        raise ValueError(f"baseline condition {args.baseline_condition!r} not in conditions")

    summaries: dict[str, str] = {}
    for condition in conditions:
        path = args.summary_dir / f"{condition}.md"
        if not path.exists():
            raise FileNotFoundError(path)
        summaries[condition] = path.read_text(encoding="utf-8")

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    scores: list[dict[str, Any]] = []
    baseline_summary = summaries[args.baseline_condition]
    for condition in conditions:
        if args.from_raw:
            print(f"Normalizing {condition} from raw output...")
            raw_text_path = args.raw_dir / f"{condition}.txt"
            if not raw_text_path.exists():
                raise FileNotFoundError(raw_text_path)
            raw_text = raw_text_path.read_text(encoding="utf-8")
            raw_json = extract_json_object(raw_text)
            score = normalize_score(condition, raw_json)
        else:
            print(f"Scoring {condition}...")
            raw_text, score = score_with_llm(
                condition,
                summaries[condition],
                baseline_summary,
                max_tokens=args.max_tokens,
                baseline_condition=args.baseline_condition,
            )
            (args.raw_dir / f"{condition}.txt").write_text(raw_text, encoding="utf-8")
        (args.raw_dir / f"{condition}.json").write_text(
            json.dumps(score, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        scores.append(score)

    write_csv(scores, args.output_csv)
    write_markdown(scores, args.output_md)

    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.output_md}")
    print(f"Wrote raw outputs to {args.raw_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
