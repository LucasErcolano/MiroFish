#!/usr/bin/env python3
"""Repository hygiene checks for tracked artifacts and high-confidence secrets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import subprocess


@dataclass(frozen=True)
class SecretFinding:
    category: str
    path: str
    line: int


_STRONG_SECRET_PATTERNS = (
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
)
_KEY_ASSIGNMENT = re.compile(
    r"(?i)(?:export\s+|\$env:)?"
    r"(?P<key>(?:LLM|OPENAI|OPENROUTER|DEEPINFRA|GEMINI|ZEP|TAVILY|HF)_API_KEY|"
    r"GRAPHITI_(?:LLM|EMBEDDER|RERANKER)_API_KEY)\s*[:=]\s*(?P<value>.*)$"
)
_PLACEHOLDER_MARKERS = (
    "replace",
    "example",
    "dummy",
    "test",
    "changeme",
    "change-me",
    "paste_",
    "your_",
    "your-",
    "<redacted>",
)


def find_text_secrets(path: str, content: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        strong_match = False
        for category, pattern in _STRONG_SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(category, path, line_number))
                strong_match = True
                break
        if strong_match:
            continue

        match = _KEY_ASSIGNMENT.search(line)
        if not match:
            continue
        value = match.group("value").split("#", 1)[0].strip().strip("\"'")
        value_lower = value.lower()
        if not value:
            continue
        if value.startswith(("$", "%", "<")) or "${" in value:
            continue
        if any(marker in value_lower for marker in _PLACEHOLDER_MARKERS):
            continue
        if any(
            marker in value_lower
            for marker in ("os.environ", "getenv", "process.env", "config.", "self.")
        ):
            continue
        if len(value) >= 16 and not any(char.isspace() for char in value):
            findings.append(
                SecretFinding("literal_api_key_assignment", path, line_number)
            )
    return findings


def is_forbidden_tracked_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    pure_path = PurePosixPath(normalized)
    parts = set(pure_path.parts)
    name = pure_path.name.lower()

    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if parts.intersection({"runs", "outputs", "node_modules", ".venv", "dist"}):
        return True
    if normalized.startswith(("backend/uploads/", "backend/data/")):
        return True
    if name in {"request_trace.json", "worldbuilding_trace.json"}:
        return True
    if pure_path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log"}:
        return True
    return False


def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0")
        if item
    ]


def scan_repository(repo_root: Path) -> tuple[list[str], list[SecretFinding]]:
    forbidden_paths: list[str] = []
    secret_findings: list[SecretFinding] = []
    for relative_path in _tracked_files(repo_root):
        if is_forbidden_tracked_path(relative_path):
            forbidden_paths.append(relative_path)

        path = repo_root / relative_path
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        content = data.decode("utf-8", errors="ignore")
        secret_findings.extend(find_text_secrets(relative_path, content))

    return sorted(set(forbidden_paths)), sorted(
        set(secret_findings), key=lambda item: (item.path, item.line, item.category)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    forbidden_paths, secret_findings = scan_repository(args.repo_root.resolve())
    if forbidden_paths:
        print("Forbidden tracked artifacts:")
        for path in forbidden_paths:
            print(f"  - {path}")
    if secret_findings:
        print("Potential secrets (values intentionally omitted):")
        for finding in secret_findings:
            print(f"  - {finding.path}:{finding.line} [{finding.category}]")
    if forbidden_paths or secret_findings:
        return 1

    print("Repository hygiene passed: no forbidden tracked artifacts or secrets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
