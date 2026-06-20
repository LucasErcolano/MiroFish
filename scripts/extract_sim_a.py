import os
import sys
import json
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.utils.llm_client import LLMClient
from backend.scripts.evaluate_ipc import calculate_mae
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))
if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"

Config.LLM_MODEL_NAME = "openrouter/meta-llama/llama-3.3-70b-instruct"

def evaluate_sim(sim_dir, sim_name):
    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        return None
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM post ORDER BY created_at DESC LIMIT 50")
    posts = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    combined_posts = "\n".join(posts)
    print(f"Extracted {len(posts)} posts for analysis.")
    
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
        
    gt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ground_truth.json'))
    with open(gt_path, 'r') as f:
        gt = json.load(f)
        
    mae, comp = calculate_mae(verdict_data, gt)
    print(f"--> {sim_name} MAE: {mae:.4f}%")
    return mae

if __name__ == "__main__":
    sim_dir = r"C:\Users\bravo\Documents\universidad\Procesamiento de Lenguaje Natural\MiroFish\backend\uploads\simulations\sim_768aaceca274"
    evaluate_sim(sim_dir, "Simulation A")
