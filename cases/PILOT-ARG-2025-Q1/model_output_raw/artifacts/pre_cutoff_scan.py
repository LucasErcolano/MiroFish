from pathlib import Path
import re, csv
base=Path(__file__).resolve().parents[2]
forbidden=[r"LLA ganó",r"40[\\.,]7",r"31[\\.,]5",r"Reuters 2025-10",r"octubre 2025 ganó"]
scan=[]
for p in (base/"input_pack_pre_x").rglob("*"):
    if p.is_file() and p.suffix.lower() not in [".pdf"]:
        txt=p.read_text(errors="ignore")
        for pat in forbidden:
            if re.search(pat,txt,re.I): scan.append((str(p.relative_to(base)),pat))
bad=[]
with open(base/"input_pack_pre_x/manifest.csv",encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["published_date"]>"2025-01-31": bad.append((r["source_id"],r["published_date"]))
print({"forbidden_matches":scan,"bad_dates":bad,"status":"PASS" if not scan and not bad else "NEEDS_REVIEW"})
