import os
from dotenv import load_dotenv
load_dotenv('.env')
api_key = os.environ.get('GEMINI_API_KEY')
print(f"DEBUG: Key is '{api_key}'")
