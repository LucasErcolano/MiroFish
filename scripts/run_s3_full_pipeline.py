import os
import sys
import time
import json
import asyncio

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.simulation_manager import SimulationManager
from backend.app.services.report_agent import ReportAgent
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

# Setup models
if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"
    Config.LLM_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"

if not Config.GRAPHITI_EMBEDDER_API_KEY:
    Config.GRAPHITI_EMBEDDER_API_KEY = Config.LLM_API_KEY
    Config.GRAPHITI_EMBEDDER_BASE_URL = Config.LLM_BASE_URL
    Config.GRAPHITI_EMBEDDER_MODEL = "openai/text-embedding-3-small"

def progress_cb(*args, **kwargs):
    if len(args) >= 3:
        print(f"[{args[0]}] {args[1]}%: {args[2]}")
    elif kwargs:
        print(f"[Progress] {kwargs}")


async def main():
    print("==================================================")
    print("S3 EXACT MAE EVALUATION PIPELINE")
    print("==================================================")
    
    # Enable S3 features
    Config.ENABLE_DEEP_SEARCH = True
    Config.SIMILARITY_THRESHOLD = 0.85
    Config.TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY')
    
    manager = SimulationManager()
    project_id = "s3_validation"
    graph_id = f"graph_s3_val_{int(time.time())}"
    
    state = manager.create_simulation(project_id, graph_id)
    sim_id = state.simulation_id
    
    print(f"1. Preparation (Deep Search + Dedup) for Sim: {sim_id}")
    theme = "Expectativas de inflación (IPC) en Argentina para 2025. Proyecciones mensuales para febrero, abril, julio y diciembre."
    
    manager.prepare_simulation(
        simulation_id=sim_id,
        simulation_requirement=theme,
        document_text="", # Zero-shot, deep search only
        progress_callback=progress_cb
    )
    
    sim_dir = manager._get_simulation_dir(sim_id)
    config_path = os.path.join(sim_dir, "simulation_config.json")
    
    # 2. Run simulation (we'll run 40 rounds)
    print("\n2. Running 40 rounds of Simulation...")
    from backend.scripts.run_twitter_simulation import TwitterSimulationRunner
    
    # Edit the config to ensure exactly 40 rounds
    with open(config_path, 'r', encoding='utf-8') as f:
        sim_config = json.load(f)
    
    sim_config["time_config"]["total_simulation_hours"] = 20 # 20 hours * 60 / 30 = 40 rounds
    sim_config["time_config"]["minutes_per_round"] = 30
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(sim_config, f, indent=2)
        
    runner = TwitterSimulationRunner(config_path)
    await runner.run()
    
    # 3. Generate Report / Verdict
    print("\n3. Generating S2 Verdict (Report Agent)...")
    agent = ReportAgent(
        graph_id=graph_id,
        simulation_id=sim_id,
        simulation_requirement=theme
    )
    report = agent.generate_report(progress_callback=progress_cb)
    
    # The report contains the sections. We need to parse predictions out of it,
    # or just use a prompt to generate the verdict.json structure required by evaluate_ipc.py
    
    print("\n4. Synthesizing verdict.json...")
    from backend.app.utils.llm_client import LLMClient
    llm = LLMClient()
    prompt = f"""
    Based on the following simulation report regarding Argentina's IPC inflation expectations for 2025, extract the numerical projections.
    
    Report:
    {report.sections[0].content[:2000]}
    
    Return a JSON exactly matching this structure (use numbers, no percentages strings). If exact months aren't clear, estimate them from the tone.
    {{
      "predictions": {{
        "delta_1_feb": {{"min_pct": 0.0, "max_pct": 0.0}},
        "delta_2_apr": {{"min_pct": 0.0, "max_pct": 0.0}},
        "delta_3_jul": {{"min_pct": 0.0, "max_pct": 0.0}},
        "delta_4_dec": {{"min_pct": 0.0, "max_pct": 0.0}}
      }}
    }}
    """
    verdict_data = llm.chat_json([
        {"role": "user", "content": prompt}
    ])
    
    verdict_path = os.path.join(sim_dir, "verdict.json")
    with open(verdict_path, 'w') as f:
        json.dump(verdict_data, f, indent=2)
        
    print(f"Verdict saved to {verdict_path}")
    
    # 5. Evaluate MAE
    print("\n5. Calculating Exact MAE...")
    from backend.scripts.evaluate_ipc import calculate_mae
    
    gt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ground_truth.json'))
    with open(gt_path, 'r') as f:
        gt = json.load(f)
        
    mae, comp = calculate_mae(verdict_data, gt)
    
    print("\n=== FINAL MAE RESULT ===")
    print(f"S2 Baseline MAE: 2.31%") # S2 Baseline
    print(f"S3 Track A+B MAE: {mae:.4f}%")
    for row in comp:
        print(f" {row['Delta']}: Truth {row['Truth']}, Pred {row['Mid']} -> Err {row['Error']}")

if __name__ == "__main__":
    asyncio.run(main())
