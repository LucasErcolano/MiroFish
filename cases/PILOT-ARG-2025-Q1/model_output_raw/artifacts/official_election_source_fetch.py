from pathlib import Path
import csv, hashlib, json, re, collections, requests, urllib3
from datetime import datetime

urllib3.disable_warnings()
BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'answer_key_post_x' / 'sources' / 'DINE_resultados_2025'
OUT.mkdir(parents=True, exist_ok=True)
accessed = '2026-05-21'


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(65536), b''):
            h.update(b)
    return h.hexdigest()

# Official DINE/MinInterior publication site. TLS cert was expired from this environment,
# so verify=False is documented in metadata; content is still archived locally for audit.
landing_url = 'https://resultados.elecciones.gob.ar/'
api_base = 'https://resultados.mininterior.gob.ar/api/'
landing = requests.get(landing_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, verify=False)
landing_path = OUT / 'resultados_electorales_landing.html'
landing_path.write_text(landing.text, encoding='utf-8', errors='ignore')

periodos = requests.get(api_base + 'menu/periodos', headers={'accept': 'application/json'}, timeout=30).json()
(OUT / 'menu_periodos.json').write_text(json.dumps(periodos, indent=2, ensure_ascii=False), encoding='utf-8')
menu = requests.get(api_base + 'menu', params={'año': 2025}, headers={'accept': 'application/json'}, timeout=30).json()
menu_path = OUT / 'menu_2025.json'
menu_path.write_text(json.dumps(menu, indent=2, ensure_ascii=False), encoding='utf-8')

election = menu[0]
districts = [(d['IdDistrito'], d['Distrito']) for c in election['Cargos'] if int(c['IdCargo']) == 3 for d in c['Distritos']]
rows = []
positive_total = 0
by_name = collections.Counter()
by_district = []
raw_dir = OUT / 'diputados_totalizado_por_distrito'
raw_dir.mkdir(exist_ok=True)
for did, dname in districts:
    params = {'año': 2025, 'recuento': 'Provisorio', 'idEleccion': 2, 'idCargo': 3, 'idDistrito': did}
    r = requests.get(api_base + 'resultado/totalizado', params=params, headers={'accept': 'application/json'}, timeout=30)
    data = r.json()
    raw_path = raw_dir / f'distrito_{did:02d}.json'
    raw_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    pos = int(data.get('positivos') or data.get('total') or 0)
    positive_total += pos
    for a in data.get('agrupaciones', []):
        name = a['nombre']
        votes = int(a['votos'])
        pct = float(str(a.get('porcentaje', '0')).replace(',', '.'))
        by_name[name] += votes
        rows.append({'district_id': did, 'district': dname, 'party': name, 'votes': votes, 'district_percentage': pct})
    by_district.append({'district_id': did, 'district': dname, 'positive_votes': pos, 'mesas_escrutadas': data.get('MesasEscrutadas'), 'electores': data.get('Electores'), 'votantes': data.get('Votantes')})

csv_path = OUT / 'computed_diputados_national_by_party.csv'
with csv_path.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['party', 'votes', 'national_percentage'])
    w.writeheader()
    for name, votes in by_name.most_common():
        w.writerow({'party': name, 'votes': votes, 'national_percentage': f'{votes / positive_total * 100:.6f}'})

district_csv = OUT / 'computed_diputados_districts.csv'
with district_csv.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['district_id', 'district', 'positive_votes', 'mesas_escrutadas', 'electores', 'votantes'])
    w.writeheader(); w.writerows(by_district)

lla_votes = sum(v for name, v in by_name.items() if 'LIBERTAD AVANZA' in name)
fp_votes = sum(v for name, v in by_name.items() if 'FUERZA PATRIA' in name)
summary = {
    'source': 'Dirección Nacional Electoral / Ministerio del Interior, Sistema de Publicación de Resultados Electorales',
    'landing_url': landing_url,
    'api_base': api_base,
    'fetched_at': datetime.now().isoformat(),
    'accessed_date': accessed,
    'tls_note': 'landing fetched with verify=False because certificate validation failed in this environment with certificate expired; API host validated normally.',
    'election': {'year': 2025, 'recount': 'Provisorio', 'idEleccion': 2, 'elecciones': 'Generales', 'cargo': 'DIPUTADO NACIONAL'},
    'districts_count': len(districts),
    'positive_votes_total_diputados': positive_total,
    'lla_votes_by_name_contains_libertad_avanza': lla_votes,
    'lla_percentage_computed': round(lla_votes / positive_total * 100, 6),
    'fuerza_patria_votes_by_name_contains_fuerza_patria': fp_votes,
    'fuerza_patria_percentage_computed': round(fp_votes / positive_total * 100, 6),
    'top_parties_raw_names': [{'party': n, 'votes': v, 'national_percentage': round(v / positive_total * 100, 6)} for n, v in by_name.most_common(12)],
    'files': {
        'landing_html': str(landing_path.relative_to(BASE)),
        'menu_2025': str(menu_path.relative_to(BASE)),
        'raw_district_json_dir': str(raw_dir.relative_to(BASE)),
        'computed_national_csv': str(csv_path.relative_to(BASE)),
        'computed_district_csv': str(district_csv.relative_to(BASE)),
    }
}
summary_path = OUT / 'official_api_computed_summary.json'
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
md_path = OUT / 'official_api_computed_summary.md'
md_path.write_text(f"""# Official DINE/MinInterior API computed summary

Source: Dirección Nacional Electoral / Ministerio del Interior — Sistema de Publicación de Resultados Electorales.

Landing URL: {landing_url}
API base: {api_base}

Election: 2025 Generales, Provisorio, Diputado Nacional.

Computed from 24 district `resultado/totalizado` API responses.

- Positive votes total, Diputados: {positive_total:,}
- Sum of party names containing `LIBERTAD AVANZA`: {lla_votes:,}
- Computed LLA national percentage over positive votes: {lla_votes / positive_total * 100:.4f}%
- Sum of party names containing `FUERZA PATRIA`: {fp_votes:,}
- Computed Fuerza Patria national percentage over positive votes: {fp_votes / positive_total * 100:.4f}%

Note: this official API computation gives ~40.66% for Diputados positive votes under names containing Libertad Avanza. Media sources saved separately report ~40.84% for combined votes/counted scope. Treat the precise 40.84 as media provisional and the official API computation as a reproducible official-source cross-check.

TLS note: landing page was fetched with certificate verification disabled because certificate validation failed as expired in this environment; API requests to `resultados.mininterior.gob.ar` succeeded normally.
""", encoding='utf-8')

# Update source manifest with official API row.
manifest = BASE / 'answer_key_post_x' / 'source_manifest.csv'
rows_manifest = list(csv.DictReader(manifest.open(encoding='utf-8')))
rows_manifest = [r for r in rows_manifest if r['source_id'] != 'GT7_DINE_API_2025']
rows_manifest.append({
    'source_id': 'GT7_DINE_API_2025',
    'title': 'Sistema de Publicación de Resultados Electorales — 2025 Generales API totalizado Diputado Nacional',
    'publisher': 'Dirección Nacional Electoral / Ministerio del Interior',
    'url': landing_url + ' and ' + api_base,
    'published_date': '2025-10-28',
    'accessed_date': accessed,
    'local_path': str(summary_path.relative_to(BASE)),
    'sha256': sha(summary_path),
    'note': 'Official accessible API cross-check. Computed from 24 district totalizado JSON responses for Diputado Nacional. LLA name-containing total: %.4f%% of positive votes; media source GT4 reports 40.84%% with 90%% counted.' % (lla_votes / positive_total * 100),
})
with manifest.open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['source_id','title','publisher','url','published_date','accessed_date','local_path','sha256','note']
    w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows_manifest)

print(json.dumps(summary, indent=2, ensure_ascii=False))
print('summary_sha256', sha(summary_path))
print('md_sha256', sha(md_path))
