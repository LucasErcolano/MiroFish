"""Summarize S2 Issue 19 Reddit condition artifacts.

This script is intentionally deterministic: it reads copied run artifacts and
does not call the backend or any LLM. Use it after the 7-condition matrix has
finished to build evidence summaries for review or downstream scoring.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RUN_DIRS = {
    "baseline": "existing-baseline-40",
    "signal-early": "existing-signal-early-40-rerun",
    "signal-mid": "existing-signal-mid-40",
    "signal-late": "existing-signal-late-40",
    "noise-early": "existing-noise-early-40",
    "noise-mid": "existing-noise-mid-40",
    "noise-late": "existing-noise-late-40",
}


def load_run_dirs(path: Path | None) -> dict[str, str]:
    if path is None:
        return DEFAULT_RUN_DIRS
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Run map must be an object: {path}")
    if "run_dirs" in data:
        data = data["run_dirs"]
    if not isinstance(data, dict):
        raise ValueError(f"Run map must contain condition -> run_dir entries: {path}")
    return {str(key): str(value) for key, value in data.items()}

FOOTBALL_PATTERNS = {
    "argentina": re.compile(r"\bargentina\b", re.IGNORECASE),
    "colombia": re.compile(r"\bcolombia\b", re.IGNORECASE),
    "messi": re.compile(r"\bmessi\b", re.IGNORECASE),
    "james": re.compile(r"\bjames\b|rodriguez|rodríguez", re.IGNORECASE),
    "football_noise": re.compile(
        r"\b(nfl|dolphins|miami heat|super bowl|football americano|basketball|nba|"
        r"transfer rumors|preseason|fan travel|ticket|tickets|resale|stadium food|"
        r"celebrity fandom|media attention|logistics)\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class ConditionPaths:
    condition: str
    run_dir: Path
    artifacts_dir: Path
    db_path: Path
    scheduled_log_path: Path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def fetch_rows(con: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    con.row_factory = sqlite3.Row
    return [dict(row) for row in con.execute(query, params)]


def count_rows(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute(f"select count(*) from {table}").fetchone()[0])


def preview(value: str | None, limit: int = 360) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def pattern_counts(texts: list[str]) -> dict[str, int]:
    joined = "\n".join(texts)
    return {name: len(pattern.findall(joined)) for name, pattern in FOOTBALL_PATTERNS.items()}


def condition_paths(runs_root: Path, condition: str, run_dir_name: str) -> ConditionPaths:
    run_dir = runs_root / run_dir_name
    artifacts_dir = run_dir / "simulation_artifacts"
    return ConditionPaths(
        condition=condition,
        run_dir=run_dir,
        artifacts_dir=artifacts_dir,
        db_path=artifacts_dir / "reddit_simulation.db",
        scheduled_log_path=artifacts_dir / "scheduled_events_fired.jsonl",
    )


def summarize_condition(paths: ConditionPaths) -> dict[str, Any]:
    if not paths.db_path.exists():
        raise FileNotFoundError(f"Missing SQLite artifact: {paths.db_path}")

    with sqlite3.connect(paths.db_path) as con:
        users = fetch_rows(
            con,
            """
            select user_id, agent_id, user_name, name, bio
            from user
            order by user_id
            """,
        )
        posts = fetch_rows(
            con,
            """
            select
              p.post_id,
              p.user_id,
              coalesce(u.name, u.user_name, cast(p.user_id as text)) as author,
              p.content,
              p.created_at,
              p.num_likes,
              p.num_dislikes,
              p.num_shares,
              (
                select count(*)
                from comment c
                where c.post_id = p.post_id
              ) as comment_count
            from post p
            left join user u on u.user_id = p.user_id
            order by p.post_id
            """,
        )
        comments = fetch_rows(
            con,
            """
            select
              c.comment_id,
              c.post_id,
              c.user_id,
              coalesce(u.name, u.user_name, cast(c.user_id as text)) as author,
              c.content,
              c.created_at,
              c.num_likes,
              c.num_dislikes
            from comment c
            left join user u on u.user_id = c.user_id
            order by c.comment_id
            """,
        )
        trace_count = count_rows(con, "trace")

    scheduled_events = read_jsonl(paths.scheduled_log_path)
    all_texts = [str(row.get("content") or "") for row in posts + comments]
    counts = pattern_counts(all_texts)

    injected_marker = "none"
    if scheduled_events:
        event_ids = {str(event.get("id", "")).lower() for event in scheduled_events}
        if "signal" in event_ids:
            injected_marker = "signal"
        elif "noise" in event_ids:
            injected_marker = "noise"
        else:
            injected_marker = ",".join(sorted(event_ids))

    likely_injected_posts = []
    for post in posts:
        content = str(post.get("content") or "")
        lower_content = content.lower()
        if (
            "[signal document]" in lower_content
            or "[noise document]" in lower_content
            or "[counter-signal document]" in lower_content
            or "# signal document" in lower_content
            or "# noise document" in lower_content
            or "# counter-signal document" in lower_content
        ):
            likely_injected_posts.append(post)

    top_discussed_posts = sorted(
        posts,
        key=lambda row: (-int(row.get("comment_count") or 0), int(row.get("post_id") or 0)),
    )[:5]

    return {
        "condition": paths.condition,
        "run_dir": str(paths.run_dir),
        "db_path": str(paths.db_path),
        "scheduled_log_path": str(paths.scheduled_log_path),
        "status": read_status(paths.artifacts_dir),
        "injected_doc": injected_marker,
        "scheduled_events": scheduled_events,
        "users": users,
        "posts": posts,
        "comments": comments,
        "trace_count": trace_count,
        "likely_injected_posts": likely_injected_posts,
        "top_discussed_posts": top_discussed_posts,
        "keyword_counts": counts,
    }


def read_status(artifacts_dir: Path) -> str:
    run_state_path = artifacts_dir / "run_state.json"
    if run_state_path.exists():
        try:
            runner_status = json.loads(run_state_path.read_text(encoding="utf-8")).get("runner_status")
            if runner_status:
                return str(runner_status)
        except json.JSONDecodeError:
            pass

    state_path = artifacts_dir / "state.json"
    if not state_path.exists():
        return "unknown"
    try:
        return str(json.loads(state_path.read_text(encoding="utf-8")).get("status", "unknown"))
    except json.JSONDecodeError:
        return "invalid_state_json"


def render_condition_markdown(summary: dict[str, Any], repo_root: Path) -> str:
    scheduled_events = summary["scheduled_events"]
    first_event = scheduled_events[0] if scheduled_events else {}
    fired_round = first_event.get("round", "-")
    fired_round_index = first_event.get("round_index", "-")
    counts = summary["keyword_counts"]

    lines = [
        f"# {summary['condition']}",
        "",
        "## Evidence",
        "",
        f"- Status: `{summary['status']}`",
        f"- Injected document: `{summary['injected_doc']}`",
        f"- Scheduled events fired: `{len(scheduled_events)}`",
        f"- Fired round: `{fired_round}`",
        f"- Fired round index: `{fired_round_index}`",
        f"- Posts: `{len(summary['posts'])}`",
        f"- Comments: `{len(summary['comments'])}`",
        f"- Traces: `{summary['trace_count']}`",
        f"- Artifact dir: `{relpath(summary['run_dir'], repo_root)}`",
        "",
        "## Keyword Counts",
        "",
        "| keyword | count |",
        "|---|---:|",
    ]
    for key in ["argentina", "colombia", "messi", "james", "football_noise"]:
        lines.append(f"| {key} | {counts[key]} |")

    lines.extend(["", "## Injected Posts", ""])
    if summary["likely_injected_posts"]:
        for post in summary["likely_injected_posts"]:
            lines.extend(
                [
                    f"### Post {post['post_id']} by {post['author']}",
                    "",
                    preview(post["content"], 900),
                    "",
                ]
            )
    else:
        lines.append("No injected post marker found in `post.content`.")
        lines.append("")

    lines.extend(["## Top Discussed Posts", ""])
    for post in summary["top_discussed_posts"]:
        lines.extend(
            [
                f"### Post {post['post_id']} by {post['author']}",
                "",
                f"- Comments: `{post['comment_count']}`",
                f"- Likes: `{post['num_likes']}`",
                "",
                preview(post["content"], 700),
                "",
            ]
        )

    lines.extend(["## Comment Sample", ""])
    for comment in summary["comments"][:8]:
        lines.extend(
            [
                f"### Comment {comment['comment_id']} on post {comment['post_id']} by {comment['author']}",
                "",
                preview(comment["content"], 500),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def relpath(path_value: str, repo_root: Path) -> str:
    path = Path(path_value)
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_csv(summaries: list[dict[str, Any]], output_path: Path, repo_root: Path) -> None:
    fields = [
        "condition",
        "status",
        "injected_doc",
        "scheduled_events",
        "fired_round",
        "fired_round_index",
        "posts",
        "comments",
        "traces",
        "argentina_mentions",
        "colombia_mentions",
        "messi_mentions",
        "james_mentions",
        "football_noise_mentions",
        "artifacts",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for summary in summaries:
            events = summary["scheduled_events"]
            first_event = events[0] if events else {}
            counts = summary["keyword_counts"]
            writer.writerow(
                {
                    "condition": summary["condition"],
                    "status": summary["status"],
                    "injected_doc": summary["injected_doc"],
                    "scheduled_events": len(events),
                    "fired_round": first_event.get("round", ""),
                    "fired_round_index": first_event.get("round_index", ""),
                    "posts": len(summary["posts"]),
                    "comments": len(summary["comments"]),
                    "traces": summary["trace_count"],
                    "argentina_mentions": counts["argentina"],
                    "colombia_mentions": counts["colombia"],
                    "messi_mentions": counts["messi"],
                    "james_mentions": counts["james"],
                    "football_noise_mentions": counts["football_noise"],
                    "artifacts": relpath(summary["run_dir"], repo_root),
                }
            )


def compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    events = summary["scheduled_events"]
    first_event = events[0] if events else {}
    return {
        "condition": summary["condition"],
        "status": summary["status"],
        "injected_doc": summary["injected_doc"],
        "scheduled_events": len(events),
        "fired_round": first_event.get("round"),
        "fired_round_index": first_event.get("round_index"),
        "posts": len(summary["posts"]),
        "comments": len(summary["comments"]),
        "traces": summary["trace_count"],
        "keyword_counts": summary["keyword_counts"],
        "likely_injected_post_ids": [row["post_id"] for row in summary["likely_injected_posts"]],
        "run_dir": summary["run_dir"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("runs/s2_issue19"),
        help="Root directory containing copied condition artifacts.",
    )
    parser.add_argument(
        "--run-map",
        type=Path,
        default=None,
        help="Optional YAML/JSON mapping from condition name to run directory name.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/condition_summaries"),
        help="Directory for generated condition Markdown summaries.",
    )
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/condition_summary_metrics.csv"),
        help="CSV output path for compact metrics.",
    )
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=Path("backtesting/case-a-s2-positional-noise/evaluation/condition_summary_metrics.json"),
        help="JSON output path for compact metrics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path.cwd()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json.parent.mkdir(parents=True, exist_ok=True)

    run_dirs = load_run_dirs(args.run_map)
    summaries = [
        summarize_condition(condition_paths(args.runs_root, condition, run_dir_name))
        for condition, run_dir_name in run_dirs.items()
    ]

    for summary in summaries:
        md = render_condition_markdown(summary, repo_root)
        (args.output_dir / f"{summary['condition']}.md").write_text(md, encoding="utf-8")

    write_csv(summaries, args.metrics_csv, repo_root)
    args.metrics_json.write_text(
        json.dumps([compact_summary(summary) for summary in summaries], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {len(summaries)} condition summaries to {args.output_dir}")
    print(f"Wrote metrics CSV to {args.metrics_csv}")
    print(f"Wrote metrics JSON to {args.metrics_json}")


if __name__ == "__main__":
    main()
