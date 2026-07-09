import yaml
import json
import argparse
import sys
import os
import time
import shutil
from pathlib import Path
from datetime import datetime

# To allow importing from backend
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

# Load env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# CRITICAL FIXES
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONUTF8"] = "1"

from app.services.simulation_manager import SimulationManager
from app.services.simulation_runner import SimulationRunner
from app.services.report_agent import ReportAgent
from app.models.project import ProjectManager
from app.config import Config

def get_cost(model_id, input_tokens, output_tokens, pricing_config):
    if model_id not in pricing_config:
        return round((input_tokens + output_tokens) / 1_000_000 * 0.1, 6)
    rates = pricing_config[model_id]
    return round((input_tokens / 1_000_000 * rates['input']) + (output_tokens / 1_000_000 * rates['output']), 6)

def run_real_mirofish_s2(model_full_name, rounds, density, output_dir, project_id, pricing_config):
    print(f"\n>>> [SIMULATION START] Model: {model_full_name} | {rounds} rounds | D{density}")
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    sim_manager = SimulationManager()
    project = ProjectManager.get_project(project_id)
    graph_id = project.graph_id or project_id
    document_text = ProjectManager.get_extracted_text(project_id) or ""

    sim_state = sim_manager.create_simulation(project_id=project_id, graph_id=graph_id, enable_twitter=True, enable_reddit=True)
    sim_id = sim_state.simulation_id

    print(f"  ID: {sim_id}. Preparing...")
    sim_manager.prepare_simulation(simulation_id=sim_id, simulation_requirement=project.simulation_requirement, document_text=document_text)

    print(f"  Simulating...")
    runner = SimulationRunner()
    runner.start_simulation(simulation_id=sim_id, platform="parallel", max_rounds=rounds)

    last_round = -1
    while True:
        status = runner.get_run_state(sim_id)
        if status and status.runner_status.value in ["completed", "failed", "stopped"]:
            if status.runner_status.value == "failed": raise Exception(status.error)
            break
        if status and status.current_round != last_round:
            print(f"    Round: {status.current_round}/{status.total_rounds}...", end="\r")
            last_round = status.current_round
        time.sleep(15)

    print("\n  Generating verdict...")
    agent = ReportAgent(graph_id=graph_id, simulation_id=sim_id, simulation_requirement=project.simulation_requirement)
    report_id = f"s2_verdict_{sim_id}"
    agent.generate_quantitative_verdict(report_id=report_id)

    # Save Stats
    duration = time.time() - start_time
    input_tokens, output_tokens = 15000 * rounds, 2000 * rounds
    cost = get_cost(model_full_name, input_tokens, output_tokens, pricing_config)

    stats = {"simulation_id": sim_id, "model": model_full_name, "rounds": rounds, "density": density, "duration_sec": round(duration, 2), "cost_usd": cost}
    with open(output_dir / "stats.json", "w") as f: json.dump(stats, f, indent=2)

    verdict_source = PROJECT_ROOT / "backend" / "uploads" / "reports" / report_id / "verdict.json"
    if verdict_source.exists(): shutil.copy(verdict_source, output_dir / "verdict.json")

    run_info = {"timestamp": datetime.now().isoformat(), "config": {"model": model_full_name, "rounds": rounds, "density": density}, "output_file": "verdict.json"}
    with open(output_dir / "run_info.json", "w") as f: json.dump(run_info, f, indent=2)
    print(f"<<< [DONE] {sim_id}. Cost: ${cost}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    with open(PROJECT_ROOT / "config_matrix.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    pricing = config.get("pricing", {})
    project_id = config["experiment_metadata"]["project_id"]
    base_dir = PROJECT_ROOT / "runs" / "s2"
    primary_model = config["baseline_model"]
    conditions = config["line5_conditions"]

    print("=== MiroFish S2 PHASE 1: Llama 3.3 Ablation Study ===")

    # In Phase 1, we ONLY run the primary model (Llama 3.3) across all conditions
    # This allows us to identify the 'Optimal Condition' before running the Ladder.
    tasks = [(primary_model, c) for c in conditions]

    if not args.execute:
        print("\n[DRY RUN] Plan for Phase 1:")
        for m, c in tasks: print(f" - {m} @ {c['id']}")
        return

    # Execution
    for model_full_name, cond in tasks:
        display_name = model_full_name.split("/")[-1]
        output_dir = base_dir / f"{cond['id']}_{display_name}"

        if output_dir.exists() and (output_dir / "verdict.json").exists():
            print(f"Skipping {output_dir.name} (exists).")
            continue

        # Routing
        api_key = os.environ.get("DEEPINFRA_API_KEY")
        base_url = "https://api.deepinfra.com/v1/openai"

        os.environ.update({"LLM_API_KEY": api_key, "LLM_BASE_URL": base_url, "LLM_MODEL_NAME": model_full_name.replace("deepinfra/", ""), "OPENAI_API_KEY": api_key, "OPENAI_BASE_URL": base_url})
        Config.LLM_API_KEY, Config.LLM_BASE_URL, Config.LLM_MODEL_NAME = api_key, base_url, model_full_name.replace("deepinfra/", "")

        try:
            run_real_mirofish_s2(model_full_name, cond["rounds"], cond["density"], output_dir, project_id, pricing)
        except Exception as e:
            print(f"Error: {e}")
            if output_dir.exists() and not (output_dir / "verdict.json").exists(): shutil.rmtree(output_dir)

    print("\n[COMPLETED] Phase 1 finished. Analyzing results to define Phase 2.")

if __name__ == "__main__":
    main()
