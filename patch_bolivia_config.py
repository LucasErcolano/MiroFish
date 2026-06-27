import json

with open("backtesting/case-b-s2-bolivia-2025-runoff/output_multiagent/multiagent_T3_R10/simulation_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Set model_map_path
config["model_map_path"] = "agent_model_map.yaml"

# Set total rounds to 20 for short simulation
config["time_config"]["total_simulation_hours"] = 20
config["time_config"]["minutes_per_round"] = 60

# Add scheduled_events for the counter-signal
counter_signal = """# Counter-Signal: Late Quiroga Lead Poll

Late campaign polling evidence points toward Jorge Quiroga:

- A late poll showed Quiroga ahead in the runoff scenario.
- Quiroga's profile may appeal to voters seeking a more explicit break with the MAS era.
- If anti-MAS coordination favors ideological clarity over coalition breadth, Quiroga could consolidate undecided voters.
"""

config["event_config"] = {
    "initial_posts": [],
    "scheduled_events": [
        {
            "id": "bolivia-counter-mid",
            "round_pct": 0.50,
            "target_platform": "reddit",
            "action": "create_post",
            "content": counter_signal,
            "poster_agent_id": 0 # Let agent 0 (Llama) post it
        }
    ]
}

with open("backtesting/s3-cross-topic-injection/multiagent_bolivia/simulation_config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
