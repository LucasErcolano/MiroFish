#!/usr/bin/env python3
"""
Línea 6 — Phase-2 per-model analysis (Issue #28).

Given one finished simulation (a model run on the comparison case), compute the
full metric set used to compare models:

1. across-persona diversity   (profiles)            — analysis.across_persona_report
2. output diversity           (DB posts/comments)   — simulation_db.output_diversity
3. posts-based temporal drift  (DB posts over rounds) — simulation_db.temporal_drift_from_posts
4. planning capture            (simulation_config)   — model-generated plan, for cross-model
                                                       planning-divergence comparison

Usage:
  backend/.venv/bin/python backend/scripts/entropy_phase2_analysis.py \
      --sim-dir backend/uploads/simulations/<sim_id> --label gemma-3-27b \
      --with-embeddings --real-embedder --output runs/linea6/phase2_<model>.json
"""

import argparse
import json
import os
import sys
from collections import Counter

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS, "..", "app", "research"))
sys.path.insert(0, os.path.join(_THIS, ".."))

from entropy import analysis, personas, simulation_db  # noqa: E402
from entropy.embedder import get_embedder  # noqa: E402


def planning_summary(sim_dir: str) -> dict:
    """Capture the model-generated plan from simulation_config.json."""
    path = os.path.join(sim_dir, "simulation_config.json")
    if not os.path.exists(path):
        return {}
    cfg = json.load(open(path, encoding="utf-8"))
    agents = cfg.get("agent_configs") or []
    tc = cfg.get("time_config") or {}
    ev = cfg.get("event_config") or {}
    reasoning = cfg.get("generation_reasoning") or ""
    return {
        "llm_model": cfg.get("llm_model"),
        "n_agents": len(agents),
        "stance_distribution": dict(Counter(a.get("stance") for a in agents if a.get("stance"))),
        "entity_type_distribution": dict(Counter(a.get("entity_type") for a in agents if a.get("entity_type"))),
        "total_simulation_hours": tc.get("total_simulation_hours"),
        "minutes_per_round": tc.get("minutes_per_round"),
        "n_initial_posts": len(ev.get("initial_posts") or []),
        "n_hot_topics": len(ev.get("hot_topics") or []),
        "reasoning_chars": len(reasoning),
        "reasoning": reasoning,  # kept for cross-model text comparison
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase-2 per-model metrics (Línea 6).")
    ap.add_argument("--sim-dir", required=True)
    ap.add_argument("--label", required=True, help="Model label, e.g. gemma-3-27b")
    ap.add_argument("--with-embeddings", action="store_true")
    ap.add_argument("--real-embedder", action="store_true")
    ap.add_argument("--no-comments", action="store_true", help="Ignore comment rows.")
    ap.add_argument("--output")
    args = ap.parse_args(argv)

    embedder = get_embedder(prefer_real=args.real_embedder) if args.with_embeddings else None

    profiles = personas.load_profiles_from_sim_dir(args.sim_dir)
    across = analysis.across_persona_report(profiles, embedder=embedder,
                                            with_embeddings=args.with_embeddings, label=args.label)

    db = simulation_db.find_sim_db(args.sim_dir)
    posts = simulation_db.load_posts(db, include_comments=not args.no_comments) if db else []
    out_div = simulation_db.output_diversity(posts, embedder=embedder, with_embeddings=args.with_embeddings)
    drift = simulation_db.temporal_drift_from_posts(posts, embedder=embedder, with_embeddings=args.with_embeddings)

    result = {
        "label": args.label,
        "sim_dir": args.sim_dir,
        "across_persona": across,
        "output_diversity": out_div,
        "temporal_drift": drift,
        "planning": planning_summary(args.sim_dir),
    }

    p = result
    print(f"\n=== Phase-2 metrics: {args.label} ===")
    print(f"  personas={p['across_persona']['n_personas']}  "
          f"cat_div={p['across_persona']['categorical_diversity_index']:.3f}  "
          f"persona_self_bleu={p['across_persona']['lexical']['self_bleu']:.3f}"
          + (f"  persona_vendi={p['across_persona']['embeddings']['vendi_score']:.3f}"
             if 'embeddings' in p['across_persona'] else ""))
    od = p["output_diversity"]
    print(f"  posts={od['n_posts']} (authors={od['n_authors']})  "
          f"out_distinct2={od['distinct_2']:.3f}  out_self_bleu={od['self_bleu']:.3f}"
          + (f"  out_vendi={od['vendi_score']:.3f}" if 'vendi_score' in od else ""))
    dr = p["temporal_drift"]["aggregate"]
    print(f"  drift: personas={dr.get('n_personas_with_drift')}  "
          f"mean_self_bleu={dr.get('mean_self_bleu')}  "
          f"mean_endpoint_dist={dr.get('mean_endpoint_distance')}")
    pl = p["planning"]
    print(f"  planning: n_agents={pl.get('n_agents')}  stance={pl.get('stance_distribution')}  "
          f"reasoning_chars={pl.get('reasoning_chars')}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
