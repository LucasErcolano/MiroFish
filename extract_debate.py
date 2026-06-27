import sqlite3
import json
import yaml

# Load agent model map
with open('agent_model_map.yaml', 'r') as f:
    model_map = yaml.safe_load(f)

def get_model(agent_id):
    if agent_id in model_map['by_agent_id']:
        return model_map['by_agent_id'][agent_id]['model']
    return model_map['default']['model']

conn = sqlite3.connect('backtesting/s3-cross-topic-injection/multiagent_football/reddit_simulation.db')
c = conn.cursor()

c.execute("SELECT user_id, action, info, created_at FROM trace WHERE action IN ('create_post', 'create_comment') ORDER BY created_at ASC")
rows = c.fetchall()

with open('C:/Users/bravo/.gemini/antigravity-cli/brain/7e0e5479-c57a-4490-afb7-040030239d61/football_debate_analysis.md', 'w', encoding='utf-8') as f:
    f.write("# S3 Football Multi-Agent Debate Analysis\n\n")
    f.write("This document tracks the interaction between the agents in the S3 Football simulation after the counter-signal was injected.\n\n")
    
    for row in rows:
        user_id = row[0]
        action = row[1]
        info = json.loads(row[2])
        created_at = row[3]
        model = get_model(user_id)
        
        f.write(f"### 🤖 Agent {user_id} ({model})\n")
        f.write(f"**Action:** {action}\n")
        if 'post_id' in info:
            f.write(f"**Targeting Post:** {info['post_id']}\n")
        
        content = info.get('content', '')
        f.write(f"**Content:**\n> {content.replace(chr(10), chr(10) + '> ')}\n\n")

print("Debate analysis written to football_debate_analysis.md")
