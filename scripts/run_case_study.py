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
from backend.app.services.deep_search import DeepSearchService
from backend.app.utils.llm_client import LLMClient
from backend.scripts.evaluate_ipc import calculate_mae
from backend.scripts.run_twitter_simulation import TwitterSimulationRunner
from backend.app.services.graph_builder import GraphBuilderService

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

async def run_simulation(sim_name, document_text, theme):
    print(f"\n==================================================")
    print(f"STARTING {sim_name}")
    print(f"==================================================")
    
    manager = SimulationManager()
    project_id = f"s3_{sim_name.lower().replace(' ', '_')}"
    
    # We will build graph directly with wait to ensure nodes are built
    builder = GraphBuilderService()
    graph_id = builder.create_graph(f"Graph {sim_name}")
    print(f"1. Preparation (Dedup) for Graph: {graph_id}")
    
    # Send directly via text batches for graph building (with deduplication inside backend)
    # Actually manager.prepare_simulation will do the Zep graph reading, so graph needs to have nodes!
    # Let's add text directly to the backend to populate it.
    # Set a robust ontology so ZepEntityReader finds them
    ontology = {
        "entity_types": [
            {"name": "Person", "description": "A human being"},
            {"name": "Organization", "description": "A company, institution or group"},
            {"name": "Concept", "description": "An abstract idea, rule or economic variable"}
        ],
        "edge_types": [
            {"name": "Knows", "source_targets": [{"source": "Person", "target": "Person"}]},
            {"name": "Affects", "source_targets": [{"source": "Concept", "target": "Concept"}]},
            {"name": "Works_For", "source_targets": [{"source": "Person", "target": "Organization"}]}
        ]
    }
    builder.set_ontology(graph_id, ontology)
    
    print("Building graph nodes...")
    episodes = builder.add_text_batches(graph_id, [document_text], batch_size=1)
    builder._wait_for_episodes(graph_id, episodes)
    time.sleep(10) # wait for index
    
    state = manager.create_simulation(project_id, graph_id)
    sim_id = state.simulation_id
    
    manager.prepare_simulation(
        simulation_id=sim_id,
        simulation_requirement=theme,
        document_text=document_text,
        progress_callback=progress_cb
    )
    
    sim_dir = manager._get_simulation_dir(sim_id)
    config_path = os.path.join(sim_dir, "simulation_config.json")
    
    # Ensure exactly 40 rounds
    with open(config_path, 'r', encoding='utf-8') as f:
        sim_config = json.load(f)
    sim_config["time_config"]["total_simulation_hours"] = 20 # 20 hours * 60 / 30 = 40 rounds
    sim_config["time_config"]["minutes_per_round"] = 30
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(sim_config, f, indent=2)
        
    print(f"\n2. Running 40 rounds for {sim_name}...")
    runner = TwitterSimulationRunner(config_path)
    await runner.run()
    
    print(f"\n3. Generating Verdict (Report Agent) for {sim_name}...")
    agent = ReportAgent(
        graph_id=graph_id,
        simulation_id=sim_id,
        simulation_requirement=theme
    )
    report = agent.generate_report(progress_callback=progress_cb)
    
    print("\n4. Synthesizing verdict.json...")
    llm = LLMClient()
    prompt = f"""
    Based on the following simulation report regarding Argentina's IPC inflation expectations for 2025, extract the numerical projections.
    Report:
    {report.sections[0].content[:3000]}
    
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
    verdict_data = llm.chat_json([{"role": "user", "content": prompt}])
    verdict_path = os.path.join(sim_dir, "verdict.json")
    with open(verdict_path, 'w') as f:
        json.dump(verdict_data, f, indent=2)
        
    print(f"\n5. Calculating Exact MAE for {sim_name}...")
    gt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ground_truth.json'))
    with open(gt_path, 'r') as f:
        gt = json.load(f)
        
    mae, _ = calculate_mae(verdict_data, gt)
    print(f"--> {sim_name} MAE: {mae:.4f}%")
    return mae

async def main():
    theme = "Expectativas de inflación (IPC) en Argentina para 2025. Proyecciones mensuales para febrero, abril, julio y diciembre."
    
    # ---- SIMULATION A (Pure Deduplication) ----
    Config.SIMILARITY_THRESHOLD = 0.85
    Config.ENABLE_DEEP_SEARCH = False
    
    # Load manual inputs
    inputs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../inputs'))
    manual_texts = []
    for f in sorted(os.listdir(inputs_dir)):
        with open(os.path.join(inputs_dir, f), 'r', encoding='utf-8') as file:
            manual_texts.append(file.read())
    combined_manual_text = "\n\n".join(manual_texts)
    
    mae_a = await run_simulation("Simulation A", combined_manual_text, theme)
    
    # ---- SIMULATION B (Pure Autonomous Deep Search) ----
    Config.ENABLE_DEEP_SEARCH = False # Disable auto-deep search in manager, we do it manually
    deep_search = DeepSearchService()
    search_theme = "Contexto macroeconómico y expectativas de inflación (IPC) de Argentina para 2025"
    research_content = deep_search.perform_research(search_theme, max_results=5, max_date="2024-12-31")
    
    mae_b = await run_simulation("Simulation B", research_content, theme)
    
    print("\n\n" + "="*50)
    print("FINAL COMPARATIVE RESULTS")
    print("="*50)
    print(f"Baseline (Sin optimizar): 2.31%")
    print(f"Simulación A (Deduplicación): {mae_a:.4f}%")
    print(f"Simulación B (Deep Search Autónomo): {mae_b:.4f}%")

if __name__ == "__main__":
    asyncio.run(main())
