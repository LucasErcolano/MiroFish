import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.deep_search import DeepSearchService
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

# Setup models as usual
if not Config.LLM_API_KEY:
    Config.LLM_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"
    Config.LLM_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"

def test_new_deep_search():
    print("Testing new Deep Search with DDG + Llama 3.3")
    ds = DeepSearchService()
    
    theme = "Javier Milei and the expected crawling peg strategy in Argentina 2025"
    print(f"Theme: {theme}")
    
    start = time.time()
    result = ds.perform_research(theme)
    end = time.time()
    
    print(f"\n--- RESULT ({end-start:.2f}s) ---")
    print(result[:1500])

if __name__ == "__main__":
    test_new_deep_search()
