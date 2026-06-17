import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.app.config import Config

print(f"GEMINI_API_KEY from Config: '{Config.GEMINI_API_KEY}'")
print(f"LLM_API_KEY from Config: '{Config.LLM_API_KEY}'")
