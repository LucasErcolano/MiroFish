import json
import os

paths = {
    "T1_R10": "backtesting/case-b-s2-bolivia-2025-runoff/output/T1_multiagent_R10",
    "T1_R40": "backtesting/case-b-s2-bolivia-2025-runoff/output/T1_multiagent_R40",
    "T3_R10": "backtesting/case-b-s2-bolivia-2025-runoff/output/T3_multiagent_R10",
    "T3_R40": "backtesting/case-b-s2-bolivia-2025-runoff/output/T3_multiagent_R40"
}

for name, path in paths.items():
    print(f"--- {name} ---")
    eval_path = os.path.join(path, "eval_result.json")
    if os.path.exists(eval_path):
        with open(eval_path, "r") as f:
            data = json.load(f)
            print(f"MAE: {data.get('mae_vote_share', 'N/A')}")
    else:
        print("eval_result.json missing")
        
    telem_path = os.path.join(path, "llm_telemetry.jsonl")
    if os.path.exists(telem_path):
        tokens_in = 0
        tokens_out = 0
        latencies = []
        with open(telem_path, "r") as f:
            for line in f:
                row = json.loads(line)
                tokens_in += row.get("prompt_tokens", 0)
                tokens_out += row.get("completion_tokens", 0)
                latencies.append(row.get("latency", 0))
        print(f"Tokens In: {tokens_in}")
        print(f"Tokens Out: {tokens_out}")
        print(f"Total Inference Latency (s): {sum(latencies):.4f}")
    else:
        print("llm_telemetry.jsonl missing")
    print()
