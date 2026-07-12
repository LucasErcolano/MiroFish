#!/usr/bin/env python3
"""Assemble temporal evidence packages from a manifest CSV."""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path


REQUIRED_COLUMNS = {
    "doc_id",
    "package",
    "path",
    "published_at",
    "source",
    "source_type",
    "role",
    "status",
}


def parse_date(value: str, row_id: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{row_id}: invalid published_at {value!r}") from exc


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def package_rows(rows: list[dict[str, str]], package: str) -> list[dict[str, str]]:
    selected = [row for row in rows if row["package"].strip().upper() == package.upper()]
    if not selected:
        raise ValueError(f"no rows found for package {package!r}")
    return selected


def assemble(manifest: Path, package: str, out: Path, allow_pending: bool, cutoff: date | None) -> None:
    rows = package_rows(read_manifest(manifest), package)
    root = Path.cwd()
    parts = [f"# Evidence package {package.upper()}", ""]

    ready_count = 0
    sources = set()
    published_dates = set()
    roles = set()

    for row in rows:
        row_id = row["doc_id"].strip()
        status = row["status"].strip().lower()
        published_at = parse_date(row["published_at"].strip(), row_id)
        if cutoff and published_at > cutoff:
            raise ValueError(
                f"{row_id}: published_at {published_at.isoformat()} is after cutoff {cutoff.isoformat()}"
            )
        sources.add(row["source"].strip())
        published_dates.add(published_at)
        roles.add(row["role"].strip().lower())

        if status != "ready":
            if allow_pending:
                parts.extend([
                    f"## {row_id} (pending)",
                    "",
                    f"Source: {row['source']}",
                    f"Published at: {published_at.isoformat()}",
                    f"Role: {row['role']}",
                    "",
                    row.get("notes", "").strip() or "Pending source document.",
                    "",
                ])
                continue
            raise ValueError(f"{row_id}: status is {status!r}; use --allow-pending to skip")

        doc_path = Path(row["path"].strip())
        if not doc_path.is_absolute():
            doc_path = root / doc_path
        if not doc_path.exists():
            raise FileNotFoundError(f"{row_id}: document not found at {doc_path}")

        ready_count += 1
        parts.extend([
            f"## {row_id}",
            "",
            f"Source: {row['source']}",
            f"Published at: {published_at.isoformat()}",
            f"Source type: {row['source_type']}",
            f"Role: {row['role']}",
            "",
            doc_path.read_text(encoding="utf-8").strip(),
            "",
        ])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")

    print(f"wrote {out}")
    print(f"ready_documents={ready_count}")
    print(f"document_dates={len(published_dates)}")
    print(f"sources={len(sources)}")
    print(f"roles={','.join(sorted(roles))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("--cutoff", help="Maximum allowed publication date, YYYY-MM-DD")
    args = parser.parse_args()

    try:
        cutoff = date.fromisoformat(args.cutoff) if args.cutoff else None
        assemble(args.manifest, args.package, args.out, args.allow_pending, cutoff)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
