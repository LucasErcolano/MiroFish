from pathlib import Path
import hashlib, json, re
from datetime import datetime
from scrapling.fetchers import Fetcher

URL = 'https://www.reuters.com/world/americas/argentines-vote-high-stakes-test-mileis-libertarian-vision-2025-10-26/'
BASE = Path(__file__).resolve().parents[2]
OUTDIR = BASE / 'answer_key_post_x' / 'sources'
OUTDIR.mkdir(parents=True, exist_ok=True)
html_path = OUTDIR / 'Reuters_20251026_scrapling_static.html'
text_path = OUTDIR / 'Reuters_20251026_scrapling_static.txt'
meta_path = OUTDIR / 'Reuters_20251026_scrapling_static_meta.json'

resp = Fetcher.get(
    URL,
    impersonate='chrome',
    stealthy_headers=True,
    timeout=45000,
    follow_redirects=True,
)
body = resp.text if hasattr(resp, 'text') else str(resp)
html_path.write_text(body, encoding='utf-8', errors='ignore')
text = re.sub(r'<(script|style)[\s\S]*?</\1>', ' ', body, flags=re.I)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
text_path.write_text(text, encoding='utf-8')
meta = {
    'url': URL,
    'fetched_at': datetime.now().isoformat(),
    'fetcher': 'scrapling.Fetcher.get',
    'status': getattr(resp, 'status', getattr(resp, 'status_code', None)),
    'reason': getattr(resp, 'reason', None),
    'html_bytes': html_path.stat().st_size,
    'text_bytes': text_path.stat().st_size,
    'html_sha256': hashlib.sha256(html_path.read_bytes()).hexdigest(),
    'text_sha256': hashlib.sha256(text_path.read_bytes()).hexdigest(),
    'contains_expected_title_terms': all(t.lower() in text.lower() for t in ['Argentina', 'Milei']),
    'contains_block_message': any(t in text.lower() for t in ['please enable js', 'captcha', 'access denied', 'blocked']),
    'text_head': text[:500],
}
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(meta, indent=2, ensure_ascii=False))
