import os
import sys
import json
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.deep_search import DeepSearchService
from backend.app.services.oasis_profile_generator import OasisProfileGenerator
from backend.app.services.zep_entity_reader import EntityNode

def test_deep_search():
    print("\n--- Testing Track B: Deep Search (Gemini Grounding) ---")
    
    # Debug: List available models
    import google.generativeai as genai
    print("Available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Could not list models: {e}")

    service = DeepSearchService()
    theme = "Recent impact of Javier Milei's fiscal policy in Argentina (June 2026)"
    print(f"Researching: {theme}...")
    
    result = service.perform_research(theme)
    
    if "GEMINI GROUNDED RESEARCH" in result:
        print("SUCCESS: Deep Search returned grounded content.")
        print(f"Content snippet: {result[:200]}...")
    else:
        print(f"FAILURE: Deep Search returned unexpected result: {result}")

def test_deduplication():
    print("\n--- Testing Track A: Semantic Deduplication ---")
    generator = OasisProfileGenerator()
    
    # Create mock entities with semantic overlap
    e1 = EntityNode(uuid="1", name="Javier Milei", labels=["person"], summary="President of Argentina, focused on fiscal balance and deregulation.", attributes={})
    e2 = EntityNode(uuid="2", name="President Milei", labels=["person"], summary="The leader of Argentina who advocates for economic liberty and zero deficit.", attributes={})
    e3 = EntityNode(uuid="3", name="Lionel Messi", labels=["person"], summary="Inter Miami football player, legendary Argentine captain.", attributes={})
    
    entities = [e1, e2, e3]
    print(f"Input: {len(entities)} entities ('Javier Milei' and 'President Milei' are redundant)")
    
    # Try with a lower threshold if 0.8 is too high
    threshold = 0.7
    try:
        unique = generator.deduplicate_entities(entities, threshold=threshold)
        print(f"Output (threshold={threshold}): {len(unique)} entities.")
        for u in unique:
            print(f" - {u.name}")
            
        if len(unique) < len(entities):
            print("SUCCESS: Redundant entities were deduplicated.")
        else:
            print("WARNING: Deduplication did not reduce the count. Check threshold or embeddings.")
    except Exception as e:
        print(f"ERROR during deduplication: {e}")

if __name__ == "__main__":
    # Ensure S3 features are enabled in Config for the test
    Config.ENABLE_DEEP_SEARCH = True
    Config.SIMILARITY_THRESHOLD = 0.7
    
    # Force GEMINI_API_KEY into environment for the library
    if Config.GEMINI_API_KEY:
        os.environ['GOOGLE_API_KEY'] = Config.GEMINI_API_KEY
    
    # Fallback for LLM_API_KEY if not set, use OpenRouter for the test
    if not Config.LLM_API_KEY:
        from dotenv import load_dotenv
        load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))
        key = os.environ.get('LLM_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
        if key:
            Config.LLM_API_KEY = key
            Config.LLM_BASE_URL = "https://openrouter.ai/api/v1"
            Config.LLM_MODEL_NAME = "openai/gpt-4o-mini"
    
    # Ensure Embedding Config is set for deduplication
    if not Config.GRAPHITI_EMBEDDER_API_KEY:
        Config.GRAPHITI_EMBEDDER_API_KEY = Config.LLM_API_KEY
        Config.GRAPHITI_EMBEDDER_BASE_URL = Config.LLM_BASE_URL
        Config.GRAPHITI_EMBEDDER_MODEL = "openai/text-embedding-3-small"
    
    print("MiroFish Spike S3 Smoke Test")
    print("============================")
    print(f"Gemini API Key: {Config.GEMINI_API_KEY[:10] if Config.GEMINI_API_KEY else 'MISSING'}...")
    print(f"LLM API Key: {Config.LLM_API_KEY[:10] if Config.LLM_API_KEY else 'MISSING'}...")
    
    test_deep_search()
    test_deduplication()
