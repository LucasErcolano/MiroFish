import json

def main():
    out_path = "backtesting/s3-cross-topic-injection/multiagent_football/reddit_profiles.json"
    
    with open(out_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)
        
    for p in profiles:
        if "user_name" in p:
            p["username"] = p["user_name"]
            
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
        
    print(f"Fixed {len(profiles)} profiles in {out_path}")
    
if __name__ == "__main__":
    main()
