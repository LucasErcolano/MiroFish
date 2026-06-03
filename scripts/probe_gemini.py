import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def probe_gemini_15():
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"Probing Gemini with key ending in ...{api_key[-5:]}")
    genai.configure(api_key=api_key)
    
    targets = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-flash-latest", "gemini-2.5-flash"]
    
    print("\n--- Model Availability Probe ---")
    for t in targets:
        model_id = f"models/{t}"
        try:
            m = genai.get_model(model_id)
            print(f"✅ {model_id} is FOUND. Display Name: {m.display_name}")
        except Exception as e:
            if "404" in str(e):
                print(f"❌ {model_id} is NOT FOUND (404)")
            else:
                print(f"⚠️ {model_id} error: {e}")

if __name__ == "__main__":
    probe_gemini_15()
