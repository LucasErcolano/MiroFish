from pathlib import Path
import requests, hashlib, csv, json, re, html, subprocess
base=Path('/home/lucas76hz/Desktop/MiroFish/cases/PILOT-ARG-2025-Q1')
for p in ['input_pack_pre_x/sources','input_pack_pre_x/excerpts','prompt_frozen','model_output_raw/artifacts','answer_key_post_x']:
    (base/p).mkdir(parents=True, exist_ok=True)
accessed='2026-05-21'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(65536), b''):
            h.update(b)
    return h.hexdigest()

def fetch(url, path):
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0 (MiroFish audit case; contact local)'},timeout=60)
    path.write_bytes(r.content)
    return r.status_code, r.headers.get('content-type',''), len(r.content)

def pdf_text(path):
    out=path.with_suffix(path.suffix+'.txt')
    subprocess.run(['pdftotext','-layout',str(path),str(out)],check=False,timeout=120)
    return out.read_text(errors='ignore') if out.exists() else ''

def html_text(path):
    raw=path.read_text(errors='ignore')
    raw=re.sub(r'<(script|style)[\s\S]*?</\1>',' ',raw,flags=re.I)
    raw=re.sub(r'<[^>]+>',' ',raw)
    raw=html.unescape(raw)
    raw=re.sub(r'\s+',' ',raw)
    return raw

def pick(text, terms, window=900):
    chunks=[]
    low=text.lower()
    for term in terms:
        i=low.find(term.lower())
        if i>=0:
            s=max(0,i-window//2); e=min(len(text),i+window//2)
            chunks.append(text[s:e].strip())
    return '\n\n---\n\n'.join(dict.fromkeys(chunks))[:6000] or text[:3000]

sources=[
 {'id':'S1_BBVA_2024Q4','title':'Argentina Economic Outlook 4Q24','publisher':'BBVA Research','url':'https://www.bbvaresearch.com/wp-content/uploads/2024/12/Argentina-Economic-Outlook-4Q24.pdf','published_date':'2024-12','file':'S1_BBVA_Argentina_Economic_Outlook_4Q24.pdf','terms':['inflation','GDP','fiscal','exchange rate','reserves','2025']},
 {'id':'S2_BCRA_CRAWL_20250116','title':'The BCRA sets the crawling peg at 1% per month','publisher':'Banco Central de la República Argentina','url':'https://www.bcra.gob.ar/en/news/el-bcra-establece-un-nuevo-sendero-de-desplazamiento-de-1-mensual-para-el-tipo-de-cambio/','published_date':'2025-01-16','file':'S2_BCRA_crawling_peg_20250116.html','terms':['1% per month','February 1','exchange rate','inflation']},
 {'id':'S3_INDEC_IPC_202412','title':'Índice de Precios al Consumidor (IPC). Cobertura nacional. Diciembre de 2024','publisher':'INDEC','url':'https://www.indec.gob.ar/uploads/informesdeprensa/ipc_01_2517A7124C09.pdf','published_date':'2025-01-14','file':'S3_INDEC_IPC_Dic2024.pdf','terms':['2,7%','117,8%','Diciembre de 2024','Nivel general']},
 {'id':'S4_MERCOPRESS_PIIE_20250128','title':"Milei's 2025 challenges: Between Argentina's mid-term elections and the IMF",'publisher':'Mercopress / PIIE syndicated analysis','url':'https://en.mercopress.com/2025/01/28/milei-s-2025-challenges-between-argentina-s-mid-term-elections-and-the-imf','published_date':'2025-01-28','file':'S4_Mercopress_Milei_2025_challenges.html','terms':['mid-term elections','IMF','Congress','October','reserves']},
 {'id':'S5_BATIMES_POLL_202501','title':"Milei's approval rating holds as Argentines worry more about jobs",'publisher':'Buenos Aires Times','url':'https://www.batimes.com.ar/news/argentina/mileis-approval-rating-holds-as-argentines-worry-more-about-jobs.phtml','published_date':'2025-01-19','file':'S5_BATimes_approval_jobs_202501.html','terms':['approval rating','jobs','January','unemployment','worry']},
 {'id':'S6_AQ_SNAPSHOT_202501','title':'Argentina: A 2025 Snapshot','publisher':'Americas Quarterly','url':'https://www.americasquarterly.org/article/argentina-a-2025-snapshot/','published_date':'2025-01-15','file':'S6_AmericasQuarterly_Argentina_2025_snapshot.html','terms':['2025 Snapshot','Milei','Congress','inflation','midterm']},
]
manifest=[]
fetch_log=[]
for s in sources:
    path=base/'input_pack_pre_x/sources'/s['file']
    status,ctype,n=fetch(s['url'],path)
    fetch_log.append({**s,'status':status,'content_type':ctype,'bytes':n})
    text = pdf_text(path) if path.suffix.lower()=='.pdf' else html_text(path)
    ex=pick(text,s['terms'])
    ex_path=base/'input_pack_pre_x/excerpts'/(s['id']+'.md')
    ex_path.write_text(f"# Excerpt {s['id']}\n\nTitle: {s['title']}\nPublisher: {s['publisher']}\nPublished date: {s['published_date']}\nURL: {s['url']}\nAllowed before x: true\n\n```text\n{ex}\n```\n",encoding='utf-8')
    reasons={
        'S1_BBVA_2024Q4':'Pre-cutoff macro forecast: inflation, GDP, fiscal, FX/reserves.',
        'S2_BCRA_CRAWL_20250116':'Pre-cutoff policy anchor: 1% monthly crawling peg from Feb 2025.',
        'S3_INDEC_IPC_202412':'Official pre-cutoff inflation baseline through Dec 2024.',
        'S4_MERCOPRESS_PIIE_20250128':'Pre-cutoff political/economic analysis of midterms, IMF and governance.',
        'S5_BATIMES_POLL_202501':'Pre-cutoff public opinion/social concerns around approval and jobs.',
        'S6_AQ_SNAPSHOT_202501':'Pre-cutoff scenario overview integrating politics and economy.'}
    manifest.append({'source_id':s['id'],'title':s['title'],'publisher':s['publisher'],'url':s['url'],'published_date':s['published_date'],'accessed_date':accessed,'allowed_before_x':'true','reason_used':reasons[s['id']],'local_path':str(path.relative_to(base)),'sha256':sha(path)})
with open(base/'input_pack_pre_x/manifest.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['source_id','title','publisher','url','published_date','accessed_date','allowed_before_x','reason_used','local_path','sha256'])
    w.writeheader(); w.writerows(manifest)
(base/'input_pack_pre_x/fetch_log.json').write_text(json.dumps(fetch_log,indent=2,ensure_ascii=False),encoding='utf-8')
seed = """# Seed Bundle — Argentina 2025 pre-cutoff

Cutoff: 2025-01-31.

## S1 — Macroeconomía
- BBVA Research describía para 2025 un escenario de desinflación, recuperación de actividad y continuidad del ajuste fiscal, con riesgos asociados a reservas, tipo de cambio y sostenibilidad social/política de la estabilización [S1_BBVA_2024Q4].
- El BCRA anunció el 16/01/2025 que desde el 1 de febrero de 2025 el sendero de desplazamiento del tipo de cambio oficial bajaría a 1% mensual, reforzando el ancla cambiaria dentro del esquema de estabilización [S2_BCRA_CRAWL_20250116].
- INDEC informaba que diciembre de 2024 cerró con IPC mensual de 2,7% y una inflación interanual todavía muy elevada, lo que dejaba a 2025 con una herencia inflacionaria significativa pero una tendencia mensual menor que al inicio del programa [S3_INDEC_IPC_202412].

## S2 — Política e instituciones
- El oficialismo llegaba al año electoral con necesidad de aumentar bancas para sostener reformas, mejorar gobernabilidad y reducir dependencia de acuerdos circunstanciales en Congreso [S4_MERCOPRESS_PIIE_20250128; S6_AQ_SNAPSHOT_202501].
- La elección legislativa de 2025 era tratada por analistas pre-corte como un test de medio término para la agenda de Milei, con interacción entre resultados económicos, negociación con el FMI y capacidad legislativa [S4_MERCOPRESS_PIIE_20250128].
- La fragmentación opositora y la relación con gobernadores/bloques legislativos aparecían como variables claves para convertir apoyo electoral en poder institucional [S4_MERCOPRESS_PIIE_20250128; S6_AQ_SNAPSHOT_202501].

## S3 — Opinión pública y tensiones sociales
- La aprobación presidencial se mantenía competitiva pese al costo social del ajuste, pero las preocupaciones por empleo, ingresos y bienestar material seguían siendo políticamente sensibles [S5_BATIMES_POLL_202501].
- La percepción pública podía depender menos del nivel anual acumulado de inflación heredado y más de la trayectoria mensual, recuperación de salarios reales, empleo y expectativas de estabilidad [S1_BBVA_2024Q4; S3_INDEC_IPC_202412; S5_BATIMES_POLL_202501].
- Tensiones persistentes pre-corte: reservas netas, sostenibilidad del crawling peg, salario real, desempleo, oposición legislativa, negociación con FMI y tolerancia social al ajuste [S1_BBVA_2024Q4; S2_BCRA_CRAWL_20250116; S4_MERCOPRESS_PIIE_20250128].

## S4 — Variables que el sistema debe considerar
- Inflación
- Salarios reales
- Desempleo
- Reservas BCRA
- Crawling peg
- Fragmentación opositora
- Gobernabilidad legislativa
"""
(base/'input_pack_pre_x/seed_bundle.md').write_text(seed,encoding='utf-8')
prompt="""Usando exclusivamente los documentos provistos fechados hasta el 31 de enero de 2025, simulá la evolución político-económica argentina durante 2025.

Respondé en formato estructurado:

1. Predicción electoral:
- Rango nacional estimado de voto para LLA.
- Probabilidad de tres escenarios:
  A) LLA <35%
  B) LLA 35-42%
  C) LLA >42%
- Impacto esperado sobre Diputados/Senado y capacidad de blindar vetos.

2. Predicción macroeconómica:
- Rango estimado de inflación acumulada 2025.
- Probabilidad de tres escenarios:
  A) <30%
  B) 30-40%
  C) >40%

3. Mecanismo causal:
- Explicar qué variable domina la percepción pública.
- Explicar cómo interactúan inflación, salarios, desempleo, reservas, oposición y gobernabilidad.

4. Riesgos:
- Principal riesgo que podría invalidar la predicción.
- Señales tempranas que deberían monitorearse.

5. Evidencia:
- Cada claim importante debe citar el source_id del input usado.
- No usar información posterior al 31/01/2025.
- Si falta evidencia, decirlo explícitamente.
"""
(base/'prompt_frozen/prompt.md').write_text(prompt,encoding='utf-8')
(base/'prompt_frozen/system_constraints.md').write_text("""# System constraints — PILOT-ARG-2025-Q1

- No usar web/browsing durante la corrida.
- No usar herramientas externas, memoria persistente, RAG externo ni documentos fuera del input pack.
- No usar ni inferir ground truth posterior al corte x = 2025-01-31.
- Formular todo resultado sobre 2025 como predicción ex ante.
- Citar cada afirmación importante con source_id del input.
- Si MiroFish intenta recuperar contexto previo, limpiar o deshabilitar memoria antes de correr.
- El output crudo no debe editarse después de la corrida.
""",encoding='utf-8')
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'PILOT-ARG-2025-Q1 verdict schema','type':'object','required':['electoral_prediction','macro_prediction','causal_mechanism','risks','evidence','temporal_integrity'],'properties':{'electoral_prediction':{'type':'object'},'macro_prediction':{'type':'object'},'causal_mechanism':{'type':'string'},'risks':{'type':'array','items':{'type':'string'}},'early_signals':{'type':'array','items':{'type':'string'}},'evidence':{'type':'array','items':{'type':'string'}},'temporal_integrity':{'type':'object'}}}
(base/'prompt_frozen/output_schema.json').write_text(json.dumps(schema,indent=2,ensure_ascii=False),encoding='utf-8')
prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()
(base/'prompt_frozen/prompt_hash.txt').write_text(prompt_hash+'  prompt.md\n',encoding='utf-8')
run_config={'case_id':'PILOT-ARG-2025-Q1','created_at':'2026-05-21T18:45:24-03:00','model':'gemma-4-31b-it','knowledge_cutoff_claim':'2025-01','web_access':False,'rag_external':False,'memory_persistent':False,'clear_previous_memory':True,'temperature':0.2,'top_p':0.8,'seed':20250131,'num_runs':3,'num_agents':'fixed_or_logged','num_rounds':'fixed_or_logged','platform_mode':'single_or_parallel_logged','output_format':'markdown_plus_json','require_citations_to_input_ids':True,'forbid_post_cutoff_facts':True,'cli_help_check':{'command':'mirofish --help && mirofish run --help','result':'BLOCKED: mirofish command not found in PATH'},'unsupported_parameters':[{'parameter':'all runtime parameters','unsupported_parameter':True,'reason':'MiroFish CLI executable not installed/available in PATH, so support could not be verified or applied.'}],'input_files':['input_pack_pre_x/sources/*','input_pack_pre_x/seed_bundle.md'],'requirement_file':'prompt_frozen/prompt.md','intended_command':'mirofish run --files input_pack_pre_x/sources/* input_pack_pre_x/seed_bundle.md --requirement "$(cat prompt_frozen/prompt.md)" --json > model_output_raw/stdout.log 2> model_output_raw/stderr.log'}
(base/'model_output_raw/run_config.json').write_text(json.dumps(run_config,indent=2,ensure_ascii=False),encoding='utf-8')
(base/'case_card.md').write_text("""# PILOT-ARG-2025-Q1

Dominio: política, macroeconomía y comportamiento electoral argentino.

Fecha de corte x: 2025-01-31.

Horizonte Δ:
- Electoral: 2025-02-01 a 2025-10-26.
- Macroeconómico: 2025-02-01 a 2025-12-31.

Pregunta central:
Usando exclusivamente documentos fechados hasta el 31/01/2025, predecir si La Libertad Avanza consolidará poder legislativo en las elecciones de octubre de 2025, qué rango de voto obtendrá, cómo cerrará la inflación anual y qué tensiones causales persistirán.

Desenlace real:
Se documenta solo en answer_key_post_x, no en input_pack_pre_x ni prompt_frozen.
""",encoding='utf-8')
(base/'README.md').write_text("""# PILOT-ARG-2025-Q1

Objetivo operativo: construir un caso piloto cualitativo y auditable para evaluar MiroFish en una predicción político-económica argentina con corte temporal estricto.

Corte temporal x: 2025-01-31.

Horizonte de predicción:
- Electoral: 2025-02-01 a 2025-10-26.
- Macroeconómico: 2025-02-01 a 2025-12-31.

Qué se puede mirar para la corrida:
- Solo documentos fechados hasta el 31/01/2025 incluidos en input_pack_pre_x/.
- seed_bundle.md como consolidación narrativa derivada exclusivamente de esas fuentes.
- prompt_frozen/ como instrucción congelada antes de ejecutar.

Qué no se puede mirar para la corrida:
- answer_key_post_x/.
- Noticias, datos, resultados electorales, inflación anual final o análisis publicados después del 31/01/2025.
- Web/browsing/RAG externo/memoria persistente durante MiroFish.

Estado de ejecución: BLOCKED por ausencia del ejecutable `mirofish` en PATH. El caso preserva configuración, fuentes, hashes, prompt y evaluación bloqueada para reproducir la corrida cuando el CLI esté disponible.
""",encoding='utf-8')
# blocked raw files before hashes
(base/'model_output_raw/mirofish_report_raw.md').write_text('# MiroFish raw report\n\nBLOCKED: no raw model report generated because `mirofish` executable was not found in PATH during CP-03/CP-07. This file is a blocking record, not a model prediction. Do not score as model output.\n',encoding='utf-8')
(base/'model_output_raw/verdict_raw.json').write_text(json.dumps({'status':'BLOCKED','reason':'mirofish command not found in PATH','is_model_output':False},indent=2),encoding='utf-8')
(base/'model_output_raw/stdout.log').write_text('',encoding='utf-8')
(base/'model_output_raw/stderr.log').write_text('/usr/bin/bash: line 1: mirofish: command not found\n',encoding='utf-8')
# answer key
post_src=base/'answer_key_post_x'/'sources'; post_src.mkdir(exist_ok=True)
indec_post=post_src/'INDEC_IPC_Dic2025.pdf'; fetch('https://www.indec.gob.ar/uploads/informesdeprensa/ipc_01_266741F036E8.pdf',indec_post)
reuters_record=post_src/'Reuters_20251026_access_blocked.html'; fetch('https://www.reuters.com/world/americas/argentines-vote-high-stakes-test-mileis-libertarian-vision-2025-10-26/',reuters_record)
(base/'answer_key_post_x/ground_truth.md').write_text("""# Ground truth posterior a x

## Resultado electoral
LLA ganó las legislativas de octubre de 2025 con aproximadamente 40,7% del voto nacional, fortaleciendo su posición legislativa. Fuente secundaria indicada para documentación: Reuters, 2025-10-26/27, “Argentina's midterm election hands decisive win to Milei's libertarian vision” (acceso automatizado bloqueado por Reuters 401; registrar copia verificable si se archiva manualmente).

## Resultado macroeconómico
Inflación acumulada 2025: 31,5%, con IPC de diciembre de 2025 de 2,8%. Fuente oficial: INDEC, “Índice de Precios al Consumidor (IPC). Cobertura nacional. Diciembre de 2025”, publicado en enero de 2026, guardado en source_manifest.csv.

## Gobernabilidad
Evaluar si el resultado permitió blindaje de vetos, mejora de negociación legislativa o aprobación presupuestaria. El eje de evaluación es si el modelo anticipó consolidación legislativa sin depender de datos post-corte.

## Tensiones persistentes
Reservas, tipo de cambio, empleo, salario real, FMI, gobernabilidad.
""",encoding='utf-8')
with open(base/'answer_key_post_x/source_manifest.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['source_id','title','publisher','url','published_date','accessed_date','local_path','sha256','note'])
    w.writeheader()
    w.writerow({'source_id':'GT1_REUTERS_20251026','title':"Argentina's midterm election hands decisive win to Milei's libertarian vision",'publisher':'Reuters','url':'https://www.reuters.com/world/americas/argentines-vote-high-stakes-test-mileis-libertarian-vision-2025-10-26/','published_date':'2025-10-26','accessed_date':accessed,'local_path':str(reuters_record.relative_to(base)),'sha256':sha(reuters_record),'note':'Automated fetch returned access-control page; user supplied Reuters fact in task prompt. Replace with licensed/exported copy if needed.'})
    w.writerow({'source_id':'GT2_INDEC_IPC_202512','title':'Índice de Precios al Consumidor (IPC). Cobertura nacional. Diciembre de 2025','publisher':'INDEC','url':'https://www.indec.gob.ar/uploads/informesdeprensa/ipc_01_266741F036E8.pdf','published_date':'2026-01-13','accessed_date':accessed,'local_path':str(indec_post.relative_to(base)),'sha256':sha(indec_post),'note':'Official post-cutoff inflation source.'})
(base/'answer_key_post_x/rubric_1_5.md').write_text("""# Rúbrica 1-5

## A. Especificidad
1 = generalidades sin rangos.
3 = predicción direccional con algunos rangos.
5 = rangos claros, escenarios probabilísticos, actores e instituciones bien definidos.

## B. Plausibilidad / alineación al desenlace
1 = escenario contrario a los hechos.
3 = acierta dirección pero falla magnitud.
5 = se acerca a voto, inflación y gobernabilidad sin sobreajustar.

## C. Cobertura
1 = mira solo una variable.
3 = cubre política + inflación, omite riesgos.
5 = integra macro, opinión pública, Congreso, BCRA, reservas, oposición y sector externo.

## D. Consistencia causal
1 = saltos lógicos.
3 = cadena causal plausible pero incompleta.
5 = mecanismo claro, trazable y basado en evidencia pre-corte.

## E. Ausencia de información posterior
1 = menciona hechos post-corte.
3 = no hay fuga obvia, pero lenguaje ambiguo.
5 = todo está formulado como predicción y citado a inputs válidos.

## F. Utilidad
1 = resumen genérico.
3 = útil para análisis retrospectivo.
5 = produce escenarios, riesgos, señales tempranas y supuestos vulnerables.
""",encoding='utf-8')
(base/'answer_key_post_x/first_eval.md').write_text("""# Primera evaluación cualitativa

Evaluator: Lucas / agente
Blind: no
Date: 2026-05-21

Estado: BLOCKED. No se puntúa porque no existe salida cruda de MiroFish; el ejecutable `mirofish` no está disponible en PATH.

| Dimensión | Score 1-5 | Evidencia del output | Comentario |
|---|---:|---|---|
| Especificidad | N/A | N/A | Requiere model_output_raw/mirofish_report_raw.md generado por MiroFish. |
| Plausibilidad | N/A | N/A | Requiere comparar output crudo contra ground truth. |
| Cobertura | N/A | N/A | Requiere output crudo. |
| Consistencia causal | N/A | N/A | Requiere output crudo. |
| Ausencia post-corte | N/A | N/A | Requiere output crudo y verificación temporal. |
| Utilidad | N/A | N/A | Requiere output crudo. |

Total: N/A /30

Notas:
- Penalizar cualquier dato imposible de saber con los inputs.
- No premiar exactitud si parece fuga temporal.
- Separar acierto direccional de justificación causal.
- Completar esta tabla solo después de una corrida real, preservando output sin editar.
""",encoding='utf-8')
(base/'answer_key_post_x/evaluator_packet.md').write_text("""# Evaluator packet — PILOT-ARG-2025-Q1

Instrucciones:
1. Evaluar solo el output crudo en `model_output_raw/mirofish_report_raw.md` contra la rúbrica.
2. Para evaluación interna previa al ground truth, NO abrir `answer_key_post_x/ground_truth.md`.
3. Verificar que cada claim importante cite source_id válido de `input_pack_pre_x/manifest.csv`.
4. Marcar como fuga temporal cualquier dato posterior al 31/01/2025 formulado como conocido y no como predicción.

Archivos a entregar al evaluador:
- `prompt_frozen/prompt.md`
- `model_output_raw/mirofish_report_raw.md` (pendiente: bloqueado hasta ejecutar MiroFish)
- `answer_key_post_x/rubric_1_5.md`
- `input_pack_pre_x/manifest.csv` para validar citas

No incluir en modo A:
- `answer_key_post_x/ground_truth.md`
- `answer_key_post_x/source_manifest.csv`
""",encoding='utf-8')
(base/'answer_key_post_x/s2_plan.md').write_text("""# S2 plan

Evaluadores: mínimo 2.

Modo A: evaluación interna sin ground truth.
- Mide especificidad, cobertura, causalidad, temporalidad, utilidad.

Modo B: evaluación posterior con ground truth.
- Agrega plausibilidad/alineación al desenlace.

Se reportará:
- score individual;
- promedio;
- desacuerdo por dimensión;
- comentarios cualitativos;
- decisión: aceptar caso, ajustar rúbrica o repetir corrida.

Estado actual: NEEDS_REVIEW/BLOCKED hasta generar output crudo real de MiroFish.
""",encoding='utf-8')
# run manifest
run_manifest={'case_id':'PILOT-ARG-2025-Q1','cutoff':'2025-01-31','horizon':{'electoral':'2025-02-01 to 2025-10-26','macro':'2025-02-01 to 2025-12-31'},'created_at':'2026-05-21T18:45:24-03:00','repo_commit':'5c824b66a638b454aeb3d972315dbeb94a2425f3','python':'Python 3.14.4','node':'v26.1.0','mirofish_cli_available':False,'blocker':'mirofish command not found','input_manifest':'input_pack_pre_x/manifest.csv','prompt_hash':prompt_hash,'run_config':'model_output_raw/run_config.json','raw_output':'model_output_raw/mirofish_report_raw.md','status':'BLOCKED_AT_CP07'}
(base/'run_manifest.json').write_text(json.dumps(run_manifest,indent=2,ensure_ascii=False),encoding='utf-8')
# hashes
allhash={}
for p in base.rglob('*'):
    if p.is_file(): allhash[str(p.relative_to(base))]=sha(p)
(base/'input_pack_pre_x/hashes.json').write_text(json.dumps({k:v for k,v in allhash.items() if k.startswith('input_pack_pre_x/') and k!='input_pack_pre_x/hashes.json'},indent=2,ensure_ascii=False),encoding='utf-8')
(base/'model_output_raw/run_hashes.json').write_text(json.dumps({k:v for k,v in allhash.items() if (k.startswith('model_output_raw/') or k.startswith('prompt_frozen/')) and k!='model_output_raw/run_hashes.json'},indent=2,ensure_ascii=False),encoding='utf-8')
# checkpoints later by validation script
print('created', base)
