import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.utils.llm_client import LLMClient
from app.config import Config
from app.services.report_agent_s2_verdict import get_s2_verdict_prompt

def test_json_output():
    models_to_test = [
        ("openrouter/qwen/qwen3-8b", "https://openrouter.ai/api/v1", os.environ.get("OPENROUTER_API_KEY")),
        ("deepinfra/google/gemma-3-27b-it", "https://api.deepinfra.com/v1/openai", os.environ.get("DEEPINFRA_API_KEY"))
    ]
    
    system_prompt = get_s2_verdict_prompt()
    user_prompt = """SIMULATION DATA SUMMARY:
The BCRA reduced interest rates. Inflation seems to be going down. BBVA predicts 3.5% for Feb, 4.0% for April, 5.0% for July and 6.0% for Dec.
Based on this data, provide the quantitative JSON verdict."""

    print("=== Testing JSON Generation for Ladder Models ===\n")
    
    for model_full_name, base_url, api_key in models_to_test:
        print(f"Testing Model: {model_full_name}")
        
        # Strip prefix for the actual LLM call
        actual_model = model_full_name
        if "openrouter/" in actual_model:
            actual_model = actual_model.replace("openrouter/", "")
        elif "deepinfra/" in actual_model:
            actual_model = actual_model.replace("deepinfra/", "")
            
        client = LLMClient(api_key=api_key, base_url=base_url, model=actual_model)
        
        try:
            response = client.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            print("[SUCCESS] Valid JSON returned.")
            print(f"Narrative: {response.get('narrative_summary')[:50]}...")
            print(f"Deltas found: {list(response.get('predictions', {}).keys())}\n")
        except Exception as e:
            print(f"[FAILED] Error generating or parsing JSON: {e}\n")

if __name__ == "__main__":
    test_json_output()
