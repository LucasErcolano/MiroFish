import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env
project_root_env = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(project_root_env)

api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
    print("Listing models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
else:
    print("GEMINI_API_KEY not found in .env")
