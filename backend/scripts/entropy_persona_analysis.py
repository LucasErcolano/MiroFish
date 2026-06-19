#!/usr/bin/env python3
"""
Línea 6 — across-persona diversity analysis CLI (Issue #28).

Phase-1 case selection: run a single model (Gemma) through `create` -> `prepare`
for each case, then point this tool at each prepared simulation's profiles. The
case with the highest categorical diversity index is the comparison case.

Usage
-----
    # one population
    python backend/scripts/entropy_persona_analysis.py \
        --sim-dir backend/uploads/simulations/<sim_id> --output report.json

    # several cases, ranked (label=path; path is a sim dir or a *_profiles file)
    python backend/scripts/entropy_persona_analysis.py \
        --case A=backend/uploads/simulations/<sim_a> \
        --case B=backend/uploads/simulations/<sim_b> \
        --case C=<.../reddit_profiles.json> \
        --with-embeddings --output ranking.json

Notes
-----
- Categorical/lexical metrics need only numpy and run with system python3.
- `--with-embeddings` uses an offline deterministic embedder by default; pass
  `--real-embedder` to use the project EmbeddingClient (requires the backend
  environment / configured embedder).
"""

import argparse
import json
import os
import sys

# Import the `entropy` package standalone (no Flask app factory needed) and also
# expose `backend/` so the real embedder can reach app.config when requested.
_THIS = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_THIS, ".."))
sys.path.insert(0, os.path.join(_BACKEND, "app", "research"))
sys.path.insert(0, _BACKEND)

from entropy import analysis, personas  # noqa: E402
from entropy.embedder import get_embedder  # noqa: E402


def _load(path: str):
    if os.path.isdir(path):
        return personas.load_profiles_from_sim_dir(path)
    return personas.load_profiles(path)


def _parse_cases(args) -> list:
    """Return [(label, path), ...] from --case / --sim-dir / --profiles."""
    cases = []
    for spec in args.case or []:
        if "=" not in spec:
            raise SystemExit(f"--case expects label=path, got: {spec}")
        label, path = spec.split("=", 1)
        cases.append((label.strip(), path.strip()))
    for d in args.sim_dir or []:
        cases.append((os.path.basename(os.path.normpath(d)), d))
    for f in args.profiles or []:
        cases.append((os.path.basename(f), f))
    return cases


def _fmt_row(label: str, rep: dict) -> str:
    cdi = rep["categorical_diversity_index"]
    vendi = rep.get("embeddings", {}).get("vendi_score")
    vendi_s = f"{vendi:7.3f}" if vendi is not None else "    n/a"
    return (
        f"{label[:18]:18s}  n={rep['n_personas']:4d}  "
        f"cat_div={cdi:6.3f}  self_bleu={rep['lexical']['self_bleu']:6.3f}  "
        f"distinct2={rep['lexical']['distinct_2']:6.3f}  vendi={vendi_s}"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Across-persona diversity / entropy analysis (Línea 6).")
    ap.add_argument("--case", action="append", help="label=path (sim dir or profiles file). Repeatable.")
    ap.add_argument("--sim-dir", action="append", help="Prepared simulation directory. Repeatable.")
    ap.add_argument("--profiles", action="append", help="A *_profiles.(json|csv) file. Repeatable.")
    ap.add_argument("--with-embeddings", action="store_true", help="Also compute Vendi / pairwise distance.")
    ap.add_argument("--real-embedder", action="store_true", help="Use the project EmbeddingClient (needs backend env).")
    ap.add_argument("--output", help="Write the full JSON report here.")
    args = ap.parse_args(argv)

    cases = _parse_cases(args)
    if not cases:
        ap.error("provide at least one of --case / --sim-dir / --profiles")

    embedder = None
    if args.with_embeddings:
        embedder = get_embedder(prefer_real=args.real_embedder)

    reports = []
    for label, path in cases:
        profiles = _load(path)
        rep = analysis.across_persona_report(
            profiles, embedder=embedder, with_embeddings=args.with_embeddings, label=label
        )
        rep["source_path"] = path
        reports.append(rep)

    ranked = analysis.rank_cases(reports)
    selected = ranked[0]["label"] if ranked else None

    print("\nAcross-persona diversity (ranked by categorical diversity index):\n")
    for rep in ranked:
        print("  " + _fmt_row(rep["label"], rep))
    if len(ranked) > 1:
        print(f"\n  -> selected comparison case: {selected}\n")

    out = {"cases": reports, "ranking": [r["label"] for r in ranked], "selected": selected}
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
