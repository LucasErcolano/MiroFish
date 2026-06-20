import os
import sys
import json
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config
from backend.app.services.oasis_profile_generator import OasisProfileGenerator
from backend.app.services.zep_entity_reader import EntityNode
from backend.app.utils.llm_client import LLMClient
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

from openai import OpenAI

def extract_entities_from_text(text: str):
    print("Extracting entities from text using LLM (OpenRouter)...")
    
    client = OpenAI(
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
    )
    
    prompt = f"""
    Extract exactly 10 distinct entities (people, organizations, institutions) from the following text.
    Intentionally include some slight variations or redundant entities that refer to the same thing (e.g. "BCRA" and "Banco Central", or "BBVA" and "BBVA Research").
    
    Return ONLY a JSON list of objects with "name", "type", and "summary". Do not use markdown blocks.
    
    TEXT:
    {text}
    """
    
    response = client.chat.completions.create(
        model=Config.LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an entity extraction system. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    content = response.choices[0].message.content
    try:
        # Clean potential markdown
        if content.startswith("```json"):
            content = content.replace("```json\n", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return []

if __name__ == "__main__":
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/uploads/projects/proj_arg_ipc_2025/extracted_text.txt'))
    with open(doc_path, 'r', encoding='utf-8') as f:
        text = f.read()
        
    print(f"Loaded input document: {len(text)} characters.")
    
    raw_entities = extract_entities_from_text(text)
    
    nodes = []
    for i, e in enumerate(raw_entities):
        nodes.append(EntityNode(
            uuid=str(i),
            name=e.get("name", "Unknown"),
            labels=[e.get("type", "Entity")],
            summary=e.get("summary", ""),
            attributes={}
        ))
        
    print(f"\n--- BASELINE (SIMULACIÓN A) ---")
    print(f"Entidades extraídas por el Grafo (sin deduplicar): {len(nodes)}")
    for n in nodes:
        print(f" - {n.name}: {n.summary[:50]}...")
        
    print(f"\n--- OPTIMIZADO (SIMULACIÓN B) ---")
    generator = OasisProfileGenerator()
    Config.SIMILARITY_THRESHOLD = 0.85
    unique_nodes = generator.deduplicate_entities(nodes, threshold=0.85)
    
    print(f"\nEntidades resultantes (Deduplicadas): {len(unique_nodes)}")
    for n in unique_nodes:
        print(f" - {n.name}")
        
    print(f"\n--- REPORTE DE AHORRO ---")
    redundant = len(nodes) - len(unique_nodes)
    print(f"Clones eliminados: {redundant}")
    print(f"Ahorro estimado en inicialización: ~{redundant * 1500} tokens")
    print(f"Ahorro estimado por ronda (40 rondas): ~{redundant * 1000 * 40} tokens")
