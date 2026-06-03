import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def test_alias_connectivity():
    api_key = os.environ.get("GEMINI_API_KEY")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # We'll try the working aliases
    models = ["gemini-flash-latest", "gemini-2.5-flash"]
    
    print("=== Testing Gemini Working Aliases (OpenAI SDK) ===")
    
    for model in models:
        print(f"\n--- Testing Alias: {model} ---")
        client = OpenAI(api_key=api_key, base_url=base_url)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'API OK'"}]
            )
            print(f"[SUCCESS] Response: {response.choices[0].message.content}")
        except Exception as e:
            print(f"[FAILED] Error: {e}")

if __name__ == "__main__":
    test_alias_connectivity()
