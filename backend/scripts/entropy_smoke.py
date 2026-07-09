#!/usr/bin/env python3
"""
Línea 6 — end-to-end smoke (Issue #28). No network, no backend venv.

Exercises the whole pipeline on synthetic data and asserts the headline
behaviors hold: diverse > homogeneous (across-persona), the run bundle stitches
question+plan+result, and changing answers drift more than repeated ones.

    python3 backend/scripts/entropy_smoke.py   # prints PASS lines, exits non-zero on failure
"""

import os
import sys
import tempfile

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS, "..", "app", "research"))

from entropy import analysis, checkpoints, temporal  # noqa: E402
from entropy.embedder import HashingEmbedder  # noqa: E402
from dataset import run_bundle  # noqa: E402

_checks = []


def check(name, cond):
    _checks.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")


def smoke_across_persona():
    print("across-persona diversity:")
    diverse = [
        {"mbti": "INTJ", "gender": "M", "country": "AR", "profession": "eng", "age": 31,
         "interested_topics": ["ai"], "persona": "a systems builder reasoning from first principles"},
        {"mbti": "ENFP", "gender": "F", "country": "BO", "profession": "doc", "age": 44,
         "interested_topics": ["health"], "persona": "a warm clinician who values human stories"},
        {"mbti": "ISTP", "gender": "X", "country": "CL", "profession": "farmer", "age": 58,
         "interested_topics": ["climate"], "persona": "a pragmatic grower attuned to weather"},
    ]
    homog = [
        {"mbti": "INTJ", "gender": "M", "country": "AR", "profession": "eng", "age": 30,
         "interested_topics": ["ai"], "persona": "an engineer who likes ai"} for _ in range(3)
    ]
    emb = HashingEmbedder(dim=64)
    d = analysis.across_persona_report(diverse, embedder=emb, with_embeddings=True, label="diverse")
    h = analysis.across_persona_report(homog, embedder=emb, with_embeddings=True, label="homog")
    check("diverse categorical_diversity_index > homogeneous",
          d["categorical_diversity_index"] > h["categorical_diversity_index"])
    check("diverse Vendi > homogeneous Vendi",
          d["embeddings"]["vendi_score"] > h["embeddings"]["vendi_score"])
    ranked = analysis.rank_cases([h, d])
    check("rank_cases selects most diverse", ranked[0]["label"] == "diverse")


def smoke_bundle():
    print("run-bundle export:")
    with tempfile.TemporaryDirectory() as root:
        sid, rid, pid = "sim_s", "rep_s", "proj_s"
        os.makedirs(os.path.join(root, "projects", pid))
        os.makedirs(os.path.join(root, "simulations", sid))
        os.makedirs(os.path.join(root, "reports", rid))
        import json
        with open(os.path.join(root, "projects", pid, "project.json"), "w") as f:
            json.dump({"project_id": pid, "simulation_requirement": "Predict X.", "files": []}, f)
        with open(os.path.join(root, "simulations", sid, "simulation_config.json"), "w") as f:
            json.dump({"simulation_id": sid, "graph_id": "g", "llm_model": "google/gemma-3-27b-it",
                       "generation_reasoning": "because", "agent_configs": [{"stance": "supporting"}]}, f)
        with open(os.path.join(root, "reports", rid, "meta.json"), "w") as f:
            json.dump({"status": "completed"}, f)
        with open(os.path.join(root, "reports", rid, "full_report.md"), "w") as f:
            f.write("# Result\nleans 52/48")
        b = run_bundle.build_bundle(uploads_root=root, project_id=pid, simulation_id=sid, report_id=rid)
        check("bundle has question", bool(b["input"]["question"]))
        check("bundle has plan reasoning", bool(b["plan"]["reasoning"]))
        check("bundle has report", "52/48" in (b["result"]["report_markdown"] or ""))
        ds = os.path.join(root, "ds.jsonl")
        rec = run_bundle.to_training_record(b)
        check("dataset append then dedup",
              run_bundle.append_to_dataset(rec, ds) and not run_bundle.append_to_dataset(rec, ds))


def smoke_temporal():
    print("temporal drift:")
    emb = HashingEmbedder(dim=64)
    same = {(1, "q", "tw"): ["alpha alpha alpha"] * 3}
    diff = {(2, "q", "tw"): ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]}
    r_same = temporal.temporal_drift_report(same, embedder=emb)
    r_diff = temporal.temporal_drift_report(diff, embedder=emb)
    check("changing answers drift more than repeated",
          r_diff["aggregate"]["mean_endpoint_distance"] > r_same["aggregate"]["mean_endpoint_distance"])
    js = temporal.stance_js_divergence({"start": ["s", "s", "s"], "end": ["o", "o", "o"]})
    check("full stance flip → JS≈1", abs(js["endpoint"] - 1.0) < 1e-6)
    # parse + sequence round-trip
    plan = checkpoints.checkpoint_rounds(6, 3)
    recs = [checkpoints.make_record(1, cp, {"id": "q", "text": "?"}, "tw", f"r-{cp['label']}") for cp in plan]
    seqs = checkpoints.responses_to_sequences(recs)
    check("sequence ordered start→end", seqs[(1, "q", "tw")] == ["r-start", "r-mid", "r-end"])


def main():
    smoke_across_persona()
    smoke_bundle()
    smoke_temporal()
    failed = [n for n, ok in _checks if not ok]
    print(f"\n{len(_checks) - len(failed)}/{len(_checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
