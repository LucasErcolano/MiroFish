import os
import sys
import time
import json
import asyncio
import sqlite3

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.simulation_manager import SimulationManager
from backend.app.services.deep_search import DeepSearchService
from backend.app.utils.llm_client import LLMClient
from backend.scripts.evaluate_ipc import calculate_mae
from backend.scripts.run_twitter_simulation import TwitterSimulationRunner
from backend.app.services.graph_builder import GraphBuilderService

from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"

# Force standard LLM for DeepSearch/Runner, but OpenRouter format for prompture
Config.LLM_MODEL_NAME = "openrouter/meta-llama/llama-3.3-70b-instruct"

if not Config.GRAPHITI_EMBEDDER_API_KEY:
    Config.GRAPHITI_EMBEDDER_API_KEY = Config.LLM_API_KEY
    Config.GRAPHITI_EMBEDDER_BASE_URL = Config.LLM_BASE_URL
    Config.GRAPHITI_EMBEDDER_MODEL = "openai/text-embedding-3-small"

def progress_cb(*args, **kwargs):
    if len(args) >= 3:
        print(f"[{args[0]}] {args[1]}%: {args[2]}")

async def run_simulation_b():
    sim_name = "Simulation B"
    print(f"\n==================================================")
    print(f"STARTING {sim_name} (Deep Search Autónomo)")
    print(f"==================================================")
    
    # Run Deep Search
    Config.ENABLE_DEEP_SEARCH = False # Do it manually
    deep_search = DeepSearchService()
    search_theme = "Contexto macroeconómico y expectativas de inflación (IPC) de Argentina para 2025"
    print(f"1. Performing Deep Search with max_date=2024-12-31")
    research_content = deep_search.perform_research(search_theme, max_results=5, max_date="2024-12-31")
    print(f"Deep search returned {len(research_content)} chars of content.")
    
    theme = "Expectativas de inflación (IPC) en Argentina para 2025. Proyecciones mensuales para febrero, abril, julio y diciembre."
    manager = SimulationManager()
    project_id = "s3_simulation_b"
    
    builder = GraphBuilderService()
    graph_id = builder.create_graph("Graph Simulation B")
    
    # Set ontology so entities are extracted correctly
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
    
    print(f"2. Preparation (Dedup) for Graph: {graph_id}")
    episodes = builder.add_text_batches(graph_id, [research_content], batch_size=1)
    builder._wait_for_episodes(graph_id, episodes)
    time.sleep(10) # wait for index
    
    state = manager.create_simulation(project_id, graph_id)
    sim_id = state.simulation_id
    
    manager.prepare_simulation(
        simulation_id=sim_id,
        simulation_requirement=theme,
        document_text=research_content,
        progress_callback=progress_cb
    )
    
    sim_dir = manager._get_simulation_dir(sim_id)
    config_path = os.path.join(sim_dir, "simulation_config.json")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        sim_config = json.load(f)
    sim_config["time_config"]["total_simulation_hours"] = 20 # 40 rounds
    sim_config["time_config"]["minutes_per_round"] = 30
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(sim_config, f, indent=2)
        
    print(f"\n3. Running 40 rounds for {sim_name}...")
    # Change back config so TwitterRunner doesn't complain
    Config.LLM_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"
    runner = TwitterSimulationRunner(config_path)
    await runner.run()
    
    print(f"\n4. Generating Verdict from DB...")
    # Change it back to openrouter/ for Promptature
    Config.LLM_MODEL_NAME = "openrouter/meta-llama/llama-3.3-70b-instruct"
    
    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM post ORDER BY created_at DESC LIMIT 50")
    posts = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    combined_posts = "\n".join(posts)
    
    llm = LLMClient()
    prompt = f"""
    Based on the following recent social media posts from an economic simulation regarding Argentina's IPC inflation expectations for 2025, extract the consensus numerical projections for the monthly inflation rate.
    
    Posts:
    {combined_posts[:8000]}
    
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

if __name__ == "__main__":
    asyncio.run(run_simulation_b())
