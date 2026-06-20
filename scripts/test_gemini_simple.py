import os
from dotenv import load_dotenv
load_dotenv('.env')
api_key = os.environ.get('GEMINI_API_KEY')
os.environ['GOOGLE_API_KEY'] = api_key

import google.generativeai as genai

print(f"Using API Key: {api_key[:10]}...")

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello")
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
