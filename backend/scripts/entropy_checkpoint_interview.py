#!/usr/bin/env python3
"""
Línea 6 — checkpoint-interview harness (Issue #28, D3/D4).

Interviews every agent with a fixed question set at start / mid / end of a
simulation, then computes intra-persona temporal drift.

The interview API (`POST /api/simulation/interview/batch`) needs the simulation
**env to be running** (it processes IPC interview commands between rounds, and
keeps waiting for commands after the loop ends). Two ways to get start/mid/end:

1. ``--live``: with the sim running, poll run-status and fire a batch interview
   when ``current_round`` crosses each checkpoint. One process, true mid-run.
2. Truncated-run fallback: prepare once, then run copies to N/3, 2N/3, N rounds;
   call this script with ``--checkpoint start|mid|end`` after each, appending to
   the same ``--responses-out``. Use when live mid-run timing isn't reliable.

Then ``--analyze`` turns the saved responses into a temporal drift report.

Examples
--------
    # inspect the plan without a server
    python backend/scripts/entropy_checkpoint_interview.py --total-rounds 72 --dry-run

    # one checkpoint now (truncated-run fallback building block)
    python backend/scripts/entropy_checkpoint_interview.py \
        --base-url http://localhost:5001 --simulation-id <sid> --platform twitter \
        --profiles <.../twitter_profiles.csv> --checkpoint start \
        --responses-out runs/linea6/<sid>_responses.json

    # compute drift from saved responses (offline)
    python backend/scripts/entropy_checkpoint_interview.py \
        --analyze --responses-out runs/linea6/<sid>_responses.json \
        --report-out runs/linea6/<sid>_drift.json
"""

import argparse
import json
import os
import sys
import time
import urllib.request

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS, "..", "app", "research"))

from entropy import checkpoints, temporal  # noqa: E402
from entropy.embedder import get_embedder  # noqa: E402
from entropy import personas  # noqa: E402


class InterviewClient:
    """Minimal urllib client for the MiroFish interview + run-status endpoints."""

    def __init__(self, base_url: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def run_status(self, simulation_id: str) -> dict:
        return self._get(f"/api/simulation/{simulation_id}/run-status")

    def interview_batch(self, simulation_id, interviews, platform=None, timeout=60) -> dict:
        payload = {"simulation_id": simulation_id, "interviews": interviews, "timeout": timeout}
        if platform:
            payload["platform"] = platform
        return self._post("/api/simulation/interview/batch", payload)


def _resolve_questions(args) -> list:
    if args.questions_file:
        with open(args.questions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return checkpoints.DEFAULT_QUESTIONS


def _resolve_agents(args) -> list:
    """Return list of (agent_id, name). From --profiles user_ids or --agents spec."""
    if args.profiles:
        profs = personas.load_profiles(args.profiles)
        out = []
        for p in profs:
            aid = p.get("user_id", p.get("agent_id"))
            if aid is None:
                continue
            out.append((int(aid), p.get("name") or p.get("username")))
        if out:
            return out
    if args.agents:
        spec = args.agents
        if "-" in spec:
            lo, hi = spec.split("-", 1)
            return [(i, None) for i in range(int(lo), int(hi) + 1)]
        return [(i, None) for i in range(int(spec))]
    return []


def _do_checkpoint(client, args, questions, agents, checkpoint, existing) -> list:
    """Batch-interview all agents for all questions at one checkpoint; return new records."""
    records = list(existing)
    name_by_id = {aid: name for aid, name in agents}
    for q in questions:
        interviews = [{"agent_id": aid, "prompt": q["text"], "platform": args.platform} for aid, _ in agents]
        resp = client.interview_batch(args.simulation_id, interviews, platform=args.platform, timeout=args.timeout)
        for item in checkpoints.parse_batch_response(resp):
            aid = item["agent_id"]
            records.append(checkpoints.make_record(
                persona_id=aid, checkpoint=checkpoint, question=q,
                platform=item["platform"], response=item["response"],
                persona_name=name_by_id.get(aid),
            ))
    return records


def _analyze(args) -> int:
    records = checkpoints.load_responses(args.responses_out)
    sequences = checkpoints.responses_to_sequences(records, platform=args.platform)
    embedder = get_embedder(prefer_real=args.real_embedder) if not args.no_embeddings else None
    report = temporal.temporal_drift_report(sequences, embedder=embedder, with_embeddings=not args.no_embeddings)
    agg = report["aggregate"]
    print("Temporal drift (intra-persona):")
    print(f"  sequences={agg['n_sequences']}  mean_self_bleu={agg['mean_self_bleu']}")
    if "mean_endpoint_distance" in agg:
        print(f"  embedder={agg['embedder']}  mean_path_length={agg['mean_path_length']:.4f}  "
              f"mean_endpoint_distance={agg['mean_endpoint_distance']:.4f}")
    if args.report_out:
        with open(args.report_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  wrote {args.report_out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Checkpoint-interview harness + temporal drift (Línea 6).")
    ap.add_argument("--base-url", default="http://localhost:5001")
    ap.add_argument("--simulation-id")
    ap.add_argument("--platform", choices=["twitter", "reddit"], default="twitter")
    ap.add_argument("--profiles", help="*_profiles.(json|csv) to read agent ids/names.")
    ap.add_argument("--agents", help="Agent count (N) or range (lo-hi) if no --profiles.")
    ap.add_argument("--questions-file", help="JSON list of {id,text}. Defaults to a built-in set.")
    ap.add_argument("--total-rounds", type=int, default=0)
    ap.add_argument("--n-checkpoints", type=int, default=3)
    ap.add_argument("--checkpoint", help="Run one checkpoint now with this label (e.g. start/mid/end).")
    ap.add_argument("--live", action="store_true", help="Poll run-status and fire all checkpoints automatically.")
    ap.add_argument("--poll-interval", type=float, default=10.0)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--responses-out", help="JSON file to read/write checkpoint responses.")
    ap.add_argument("--analyze", action="store_true", help="Compute the temporal drift report from --responses-out.")
    ap.add_argument("--report-out", help="Where to write the drift report JSON.")
    ap.add_argument("--no-embeddings", action="store_true", help="Skip embedding drift (Self-BLEU only).")
    ap.add_argument("--real-embedder", action="store_true", help="Use the project EmbeddingClient for drift.")
    ap.add_argument("--dry-run", action="store_true", help="Print the checkpoint plan and exit (no server).")
    args = ap.parse_args(argv)

    plan = checkpoint_plan = checkpoints.checkpoint_rounds(args.total_rounds, args.n_checkpoints)

    if args.dry_run:
        print(f"Checkpoint plan for total_rounds={args.total_rounds}, n={args.n_checkpoints}:")
        for cp in plan:
            print(f"  {cp['label']:6s} -> round {cp['round']}")
        print(f"questions: {[q['id'] for q in _resolve_questions(args)]}")
        return 0

    if args.analyze:
        if not args.responses_out:
            ap.error("--analyze requires --responses-out")
        return _analyze(args)

    if not args.simulation_id or not args.responses_out:
        ap.error("interviewing requires --simulation-id and --responses-out (or use --dry-run/--analyze)")

    client = InterviewClient(args.base_url, timeout=max(args.timeout + 10, 120))
    questions = _resolve_questions(args)
    agents = _resolve_agents(args)
    if not agents:
        ap.error("no agents resolved — pass --profiles or --agents")

    existing = checkpoints.load_responses(args.responses_out) if os.path.exists(args.responses_out) else []

    if args.checkpoint:
        cp = next((c for c in plan if c["label"] == args.checkpoint),
                  {"label": args.checkpoint, "round": None, "order": len(existing)})
        records = _do_checkpoint(client, args, questions, agents, cp, existing)
        checkpoints.save_responses(records, args.responses_out)
        print(f"checkpoint '{cp['label']}': {len(records) - len(existing)} new records -> {args.responses_out}")
        return 0

    if args.live:
        records = existing
        done = set()
        while len(done) < len(plan):
            status = client.run_status(args.simulation_id).get("data", {})
            current = status.get("current_round", 0)
            total = status.get("total_rounds") or args.total_rounds or 0
            completed = (
                status.get("runner_status") == "completed"
                or bool(status.get("twitter_completed"))
                or (total and current >= total)
            )
            for cp in plan:
                if cp["label"] in done:
                    continue
                if current >= cp["round"] or (completed and cp["label"] == plan[-1]["label"]):
                    records = _do_checkpoint(client, args, questions, agents, cp, records)
                    checkpoints.save_responses(records, args.responses_out)
                    done.add(cp["label"])
                    print(f"  checkpoint '{cp['label']}' done at round ~{current}")
            if completed:
                break
            time.sleep(args.poll_interval)
        print(f"live capture complete -> {args.responses_out}")
        return 0

    ap.error("nothing to do: pass --dry-run, --checkpoint, --live, or --analyze")


if __name__ == "__main__":
    raise SystemExit(main())
