import json
import os
import sys

def main():
    trace_path = "backtesting/s3-cross-topic-injection/multiagent_football/worldbuilding_trace.json"
    out_path = "backtesting/s3-cross-topic-injection/multiagent_football/reddit_profiles.json"
    
    with open(trace_path, "r", encoding="utf-8") as f:
        trace = json.load(f)
        
    profiles = []
    
    # Map entities to profiles
    entities = trace.get("entities", {})
    # Get generation steps
    gens = {}
    for step in trace.get("trace", []):
        if step.get("action") == "generate_profile" and step.get("status") == "success":
            ent_id = step.get("entity_id")
            if ent_id:
                try:
                    out = step.get("output_text")
                    if out.startswith("```json"):
                        out = out.split("```json")[1].split("```")[0]
                    elif out.startswith("```"):
                        out = out.split("```")[1].split("```")[0]
                    gens[ent_id] = json.loads(out)
                except Exception as e:
                    print(f"Failed to parse for {ent_id}: {e}")
                    
    agent_id_counter = 0
    for ent_id, ent_data in entities.items():
        if ent_id in gens:
            p = gens[ent_id]
            p["agent_id"] = agent_id_counter
            profiles.append(p)
            agent_id_counter += 1
            
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(profiles)} profiles to {out_path}")
    
if __name__ == "__main__":
    main()
