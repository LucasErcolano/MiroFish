import sqlite3
import json

def extract(db_path, out_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT info FROM trace WHERE action IN ('create_post', 'create_comment')")
    with open(out_path, 'w', encoding='utf-8') as f:
        for row in c.fetchall():
            info = json.loads(row[0])
            content = info.get('content', '')
            f.write(content + "\n---\n")

extract('backtesting/case-b-s2-bolivia-2025-runoff/output_multiagent/multiagent_T3_R10/reddit_simulation.db', 't3_r10_forum.txt')
extract('backtesting/case-b-s2-bolivia-2025-runoff/output_multiagent/multiagent_T3_R40/reddit_simulation.db', 't3_r40_forum.txt')
