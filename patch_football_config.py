import json

with open("backtesting/s3-cross-topic-injection/multiagent_football/simulation_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Set model_map_path
config["model_map_path"] = "agent_model_map.yaml"

# Set total rounds to 20
config["time_config"]["total_simulation_hours"] = 20
config["time_config"]["minutes_per_round"] = 60

# Add scheduled_events for the counter-signal
counter_signal = """# Counter-Signal: Colombia Upside

Colombia has a realistic path to winning:

- The team entered the final with high attacking momentum and a long unbeaten run.
- James Rodriguez had been creating high-value chances throughout the tournament.
- Colombia's set pieces and transitions can punish a cautious opponent.
- Argentina may be more vulnerable if Messi is physically limited.
"""

config["event_config"] = {
    "initial_posts": [],
    "scheduled_events": [
        {
            "id": "football-counter-mid",
            "round_pct": 0.50,
            "target_platform": "reddit",
            "action": "create_post",
            "content": counter_signal,
            "poster_agent_id": 0 # Let agent 0 (Llama) post it
        }
    ]
}

with open("backtesting/s3-cross-topic-injection/multiagent_football/simulation_config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
