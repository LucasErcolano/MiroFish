
import os
import sys
import time
import json
import shutil

# Ensure we are in the backend directory context for imports
sys.path.append(os.path.join(os.getcwd(), 'backend'))
sys.path.append(os.getcwd())

# Configuration - NO MOCKS
os.environ["USE_EXPERIMENTAL_MEMORY"] = "true"
os.environ["ZEP_API_KEY"] = "not_needed"
# Point to a real data dir for the benchmark
BENCHMARK_DATA_DIR = "backend/data/benchmark_run"
os.environ["DATA_DIR"] = BENCHMARK_DATA_DIR

from app.services.zep_graph_memory_updater import ZepGraphMemoryUpdater, AgentActivity
from app.services.zep_tools import ZepToolsService
from app.config import Config

def run_empirical_benchmark():
    sim_id = "spike_empirical_validation"
    graph_id = "real_world_graph"
    
    print(f"=== SPIKE S1 EMPIRICAL BENCHMARK ===")
    print(f"Mode: USE_EXPERIMENTAL_MEMORY=true")
    
    if os.path.exists(BENCHMARK_DATA_DIR):
        shutil.rmtree(BENCHMARK_DATA_DIR)
    os.makedirs(BENCHMARK_DATA_DIR)

    # 1. Measurement of Initialization
    start_init = time.time()
    updater = ZepGraphMemoryUpdater(graph_id=graph_id, simulation_id=sim_id)
    end_init = time.time()
    print(f"[METRIC] Initialization time: {end_init - start_init:.4f}s")

    # 2. Ingestion of a 10-activity batch (Simulating a heavy round)
    activities = []
    for i in range(10):
        activities.append(AgentActivity(
            platform="twitter",
            agent_id=i,
            agent_name=f"User_{i}",
            action_type="CREATE_POST",
            action_args={"content": f"Empirical evidence message number {i}. Baseline vs Experimental check."},
            round_num=1,
            timestamp=str(time.time())
        ))

    print(f"Ingesting {len(activities)} activities...")
    start_ingest = time.time()
    # Direct call to bypass threading and measure raw provider speed
    updater._send_batch_activities(activities, "twitter")
    end_ingest = time.time()
    
    ingest_latency = end_ingest - start_ingest
    print(f"[METRIC] Batch Ingestion Latency: {ingest_latency:.4f}s")
    print(f"[METRIC] Avg Latency per item: {ingest_latency/len(activities):.4f}s")

    # 3. Retrieval Test
    print("\nRetrieving evidence...")
    tools = ZepToolsService(simulation_id=sim_id)
    start_retrieval = time.time()
    # We search for the specific content we ingested
    results = tools.search_graph(graph_id=graph_id, query="Empirical evidence check", limit=3)
    end_retrieval = time.time()
    
    print(f"[METRIC] Retrieval Latency: {end_retrieval - start_retrieval:.4f}s")
    print(f"Found {len(results.facts)} facts.")
    for f in results.facts:
        print(f"  Fact: {f[:100]}...")

    # Force save of core memory to ensure file exists for trace
    if hasattr(updater.provider, 'save_core_memory'):
        updater.provider.save_core_memory(updater.provider.core_memory)

    # 4. Verify Physical Files
    # Note: Config.DATA_DIR might have been resolved differently internally
    # We use the internal path to be sure
    actual_data_dir = Config.DATA_DIR
    sim_dir = os.path.join(actual_data_dir, 'simulations', sim_id)
    chroma_path = os.path.join(sim_dir, 'chroma_db')
    core_path = os.path.join(sim_dir, 'core_memory.json')
    
    print(f"\nChecking data in actual path: {os.path.abspath(sim_dir)}")
    print("\n--- Physical Evidence Trace ---")
    if os.path.exists(chroma_path):
        size = sum(os.path.getsize(os.path.join(dirpath,f)) for dirpath, dirnames, filenames in os.walk(chroma_path) for f in filenames)/1024
        print(f"✔ ChromaDB Folder: Created ({size:.2f} KB)")
    else:
        print(f"✘ ChromaDB Folder: NOT FOUND at {chroma_path}")
        # List simulation dir to debug
        if os.path.exists(sim_dir):
            print(f"  Contents of {sim_dir}: {os.listdir(sim_dir)}")
        
    if os.path.exists(core_path):
        print(f"✔ Core Memory File: Created")
        with open(core_path, 'r') as f:
            core = json.load(f)
            print(f"  Content Persona: {core.get('persona')}")
    else:
        print(f"✘ Core Memory File: NOT FOUND at {core_path}")

    # Report Stats
    stats = updater.get_stats()
    print(f"\nFinal Stats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    run_empirical_benchmark()
