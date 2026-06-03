import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def list_gemini_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"Listing models with key: {api_key[:10]}...")
    genai.configure(api_key=api_key)
    try:
        models = genai.list_models()
        print("Available Models:")
        for m in models:
            print(f" - {m.name} (Methods: {m.supported_generation_methods})")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
