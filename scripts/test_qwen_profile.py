import os
import sys
from pathlib import Path
import json
from pprint import pprint

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.utils.llm_client import LLMClient
from app.services.oasis_profile_generator import OasisProfileGenerator

def test_qwen_profile():
    print("=== Testing Qwen3 Profile Generation ===")
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"
    model = "qwen/qwen3-8b"
    
    gen = OasisProfileGenerator(model_name=model, api_key=api_key, base_url=base_url)
    
    prompt = gen._build_group_persona_prompt(
        "FMI", 
        "InternationalOrganization", 
        "International Monetary Fund", 
        {}, 
        "FMI provides funds to Argentina."
    )
    
    sys_prompt = gen._get_system_prompt(False)
    
    client = LLMClient(api_key=api_key, base_url=base_url, model=model)
    
    print("\n--- Sending request to Qwen3 ---")
    
    try:
        # Requesting raw chat to see what it actually outputs
        response = client.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        print(f"\nRAW OUTPUT:\n{content}\n")
        
        # Now pass it through our try_fix_json logic
        try:
            parsed = json.loads(content)
            print("[SUCCESS] Parsed natively.")
        except json.JSONDecodeError as e:
            print(f"[FAILED Native Parse]: {e}")
            fixed = gen._try_fix_json(content, "FMI", "InternationalOrganization", "IMF")
            print("\nFIX ATTEMPT RESULT:")
            pprint(fixed)
            
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    test_qwen_profile()
