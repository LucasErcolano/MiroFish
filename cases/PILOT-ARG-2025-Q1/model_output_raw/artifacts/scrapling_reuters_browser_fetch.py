from pathlib import Path
import hashlib, json, re
from datetime import datetime
from scrapling.fetchers import StealthyFetcher, DynamicFetcher

URL = 'https://www.reuters.com/world/americas/argentines-vote-high-stakes-test-mileis-libertarian-vision-2025-10-26/'
BASE = Path(__file__).resolve().parents[2]
OUTDIR = BASE / 'answer_key_post_x' / 'sources'
OUTDIR.mkdir(parents=True, exist_ok=True)
results=[]

for name, fetcher, kwargs in [
    ('scrapling.StealthyFetcher.fetch', StealthyFetcher.fetch, {'headless': True, 'timeout': 60000, 'network_idle': True}),
    ('scrapling.DynamicFetcher.fetch', DynamicFetcher.fetch, {'headless': True, 'timeout': 60000, 'network_idle': True}),
]:
    safe = name.replace('.', '_')
    html_path = OUTDIR / f'Reuters_20251026_{safe}.html'
    text_path = OUTDIR / f'Reuters_20251026_{safe}.txt'
    meta_path = OUTDIR / f'Reuters_20251026_{safe}_meta.json'
    try:
        resp = fetcher(URL, **kwargs)
        body = resp.text if hasattr(resp, 'text') else str(resp)
        status = getattr(resp, 'status', getattr(resp, 'status_code', None))
        err = None
    except Exception as e:
        body = ''
        status = None
        err = repr(e)
    html_path.write_text(body, encoding='utf-8', errors='ignore')
    text = re.sub(r'<(script|style)[\s\S]*?</\1>', ' ', body, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text_path.write_text(text, encoding='utf-8')
    meta = {
        'url': URL,
        'fetched_at': datetime.now().isoformat(),
        'fetcher': name,
        'kwargs': kwargs,
        'status': status,
        'error': err,
        'html_bytes': html_path.stat().st_size,
        'text_bytes': text_path.stat().st_size,
        'html_sha256': hashlib.sha256(html_path.read_bytes()).hexdigest(),
        'text_sha256': hashlib.sha256(text_path.read_bytes()).hexdigest(),
        'contains_expected_terms': all(t.lower() in text.lower() for t in ['argentina', 'milei']),
        'contains_result_terms': any(t.lower() in text.lower() for t in ['40.7', '40,7', 'decisive win', 'landslide', 'midterm']),
        'contains_block_message': any(t in text.lower() for t in ['please enable js', 'captcha', 'access denied', 'blocked', 'verify you are human']),
        'text_head': text[:700],
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    results.append(meta)
print(json.dumps(results, indent=2, ensure_ascii=False))
