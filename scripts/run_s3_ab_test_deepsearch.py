import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.simulation_manager import SimulationManager
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

# Setup models as usual
if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"
    Config.LLM_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"

# Ensure embeddings configured
if not Config.GRAPHITI_EMBEDDER_API_KEY:
    Config.GRAPHITI_EMBEDDER_API_KEY = Config.LLM_API_KEY
    Config.GRAPHITI_EMBEDDER_BASE_URL = Config.LLM_BASE_URL
    Config.GRAPHITI_EMBEDDER_MODEL = "openai/text-embedding-3-small"

def progress_cb(stage, pct, msg):
    print(f"[{stage}] {pct}%: {msg}")

def run_test(name, use_deep_search, theme, document_path=None):
    print(f"\n======================================")
    print(f"RUNNING TEST: {name}")
    print(f"DEEP SEARCH ENABLED: {use_deep_search}")
    print(f"======================================")
    
    Config.ENABLE_DEEP_SEARCH = use_deep_search
    Config.SIMILARITY_THRESHOLD = 0.85 # Let's keep dedup on to save time
    
    document_text = ""
    if document_path:
        with open(document_path, 'r', encoding='utf-8') as f:
            document_text = f.read()

    manager = SimulationManager()
    project_id = "test_project_ds"
    graph_id = f"test_graph_{name}_{int(time.time())}"
    
    state = manager.create_simulation(project_id, graph_id)
    
    try:
        manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement=theme,
            document_text=document_text,
            progress_callback=progress_cb
        )
        
        sim_dir = manager._get_simulation_dir(state.simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
        
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
            
        print(f"\n[RESULT] {name} Generated {len(profiles)} agents.")
        
        # Also check if deep search file exists
        ds_file = os.path.join(sim_dir, "deep_search_result.txt")
        has_ds = os.path.exists(ds_file)
        print(f"[RESULT] {name} Deep Search File Created: {has_ds}")
        
        return len(profiles), state.simulation_id, sim_dir
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 0, state.simulation_id, ""

if __name__ == "__main__":
    # Ensure Gemini Key is configured for Deep Search
    Config.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if Config.GEMINI_API_KEY:
        os.environ['GOOGLE_API_KEY'] = Config.GEMINI_API_KEY
        
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/uploads/projects/proj_arg_ipc_2025/extracted_text.txt'))
    theme = "Expectativas de devaluación y crawling peg del BCRA para enero 2025 en Argentina. Consultoras privadas como Macro y BBVA."
    
    # 1. Run Baseline (No Deep Search, provided text)
    # agents_a, sim_id_a, dir_a = run_test("BASELINE_NO_DS", False, theme, doc_path)
    
    # 2. Run Optimized (Deep Search ONLY, NO provided text)
    agents_b, sim_id_b, dir_b = run_test("OPTIMIZED_DS_ONLY", True, theme, None)
    
    print("\n\n=== RESULTS ===")
    print(f"Deep Search Agents Generated: {agents_b}")
