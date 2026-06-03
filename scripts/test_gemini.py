import sys
import os
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

# Load env before anything else
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.utils.llm_client import LLMClient
from app.config import Config

def test_gemini_connectivity():
    print("=== Testing Gemini API Connectivity (OpenAI-Compatible) ===")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
    model_name = "gemini-1.5-flash"
    
    print(f"Model: {model_name}")
    print(f"Base URL: {base_url}")
    
    # Update Config singleton
    Config.LLM_API_KEY = api_key
    Config.LLM_BASE_URL = base_url
    Config.LLM_MODEL_NAME = model_name
    
    try:
        client = LLMClient(api_key=api_key, base_url=base_url, model=model_name)
        response = client.chat([{"role": "user", "content": "Say 'API OK'"}])
        print(f"\n[SUCCESS] Gemini Response: {response}")
        return True
    except Exception as e:
        print(f"\n[FAILED] Gemini connectivity error: {e}")
        return False

if __name__ == "__main__":
    test_gemini_connectivity()
