import json
import glob
from pathlib import Path

for f in glob.glob('runs/s2/*Llama*/stats.json'):
    if 'rep' not in f:
        data = json.load(open(f))
        cond = Path(f).parent.name.split('_')[0]
        print(f"{cond} | ${data['cost_usd']} | {data['duration_sec']}s")
