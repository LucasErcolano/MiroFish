import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.simulation_manager import SimulationManager
from dotenv import load_dotenv

# Ensure environment is loaded and LLM configured
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))
if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"
    Config.LLM_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"

# Ensure embeddings configured
if not Config.GRAPHITI_EMBEDDER_API_KEY:
    Config.GRAPHITI_EMBEDDER_API_KEY = Config.LLM_API_KEY
    Config.GRAPHITI_EMBEDDER_BASE_URL = Config.LLM_BASE_URL
    Config.GRAPHITI_EMBEDDER_MODEL = "openai/text-embedding-3-small"

from backend.app.services.graph_builder import GraphBuilderService

def progress_cb(stage, pct, msg, **kwargs):
    print(f"[{stage}] {pct}%: {msg}")

def run_test(name, dedup_threshold, document_path):
    print(f"\n======================================")
    print(f"RUNNING TEST: {name}")
    print(f"THRESHOLD: {dedup_threshold}")
    print(f"======================================")
    
    Config.SIMILARITY_THRESHOLD = dedup_threshold
    Config.ENABLE_DEEP_SEARCH = False
    
    with open(document_path, 'r', encoding='utf-8') as f:
        document_text = f.read()

    manager = SimulationManager()
    project_id = "test_project"
    graph_id = f"test_graph_{name}_{int(time.time())}"
    
    print(f"Building Graph: {graph_id}...")
    builder = GraphBuilderService()
    # Simple build logic
    builder.backend.add_document(graph_id, document_text, "test_doc")
    print(f"Graph built.")
    
    state = manager.create_simulation(project_id, graph_id)
    
    try:
        manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement="Analyze the economic expectations.",
            document_text=document_text,
            progress_callback=progress_cb
        )
        
        sim_dir = manager._get_simulation_dir(state.simulation_id)
        profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
        
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
            
        print(f"\n[RESULT] {name} Generated {len(profiles)} agents.")
        return len(profiles), state.simulation_id, sim_dir
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 0, state.simulation_id, ""

if __name__ == "__main__":
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/uploads/projects/proj_arg_ipc_2025/extracted_text.txt'))
    
    # 1. Run Baseline
    agents_a, sim_id_a, dir_a = run_test("BASELINE_NO_DEDUP", 0.0, doc_path)
    
    # 2. Run Optimized
    agents_b, sim_id_b, dir_b = run_test("OPTIMIZED_DEDUP_0_7", 0.7, doc_path)
    
    print("\n\n=== RESULTS ===")
    print(f"Baseline Agents: {agents_a}")
    print(f"Optimized Agents: {agents_b}")
    print(f"Reduction: {agents_a - agents_b} agents")
