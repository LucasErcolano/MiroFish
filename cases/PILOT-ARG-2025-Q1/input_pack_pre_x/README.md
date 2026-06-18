# Input Pack Pre-X — S1 MiroFish

Case ID: PILOT-ARG-2025-Q1
Cutoff exacto: 2025-01-31 23:59 Argentina local time.

## Regla de exclusión post-corte

Este directorio puede ser leído por MiroFish S1. Por lo tanto, contiene únicamente fuentes publicadas en o antes del 31/01/2025. No debe contener ground truth ni fuentes posteriores. Todo material post-corte pertenece a `answer_key_post_x/` y queda fuera del input.

## Archivos incluidos

Core:
- sources/MACRO_01_BBVA_Argentina_Economic_Outlook_Dec2024.pdf
- sources/MONETARY_01_BCRA_Crawling_Peg_1pct_20250116.html
- sources/MACRO_02_INDEC_IPC_Diciembre_2024.pdf
- sources/MACRO_03_BCRA_REM_Diciembre_2024.pdf
- sources/FISCAL_01_MECON_Cierre_Fiscal_2024.html
- sources/GEO_01_IMF_ExPost_Evaluation_202501.pdf
- sources/POL_01_AmericasQuarterly_Argentina_2025_Snapshot.html
- sources/POLL_01_CB_Consultora_Diciembre_2024.pdf
- sources/SOCIAL_01_UCA_ODSA_Informe_Subsistencia_20241205.pdf
- sources/INST_01_Diputados_Veto_Ley_Jubilatoria_20240911.html

Supporting:
- sources/INST_02_Chequeado_Veto_Jubilatorio_Conteo_20240911.html
- sources/MONETARY_02_BCRA_Informe_Monetario_Diciembre_2024.pdf
- sources/MACRO_04_WorldBank_GEP_Jan2025_LAC.pdf

Generated audit files:
- manifest.csv
- hashes.json
- seed_bundle.md
- README.md
- fetch_log.json

## Fuentes reemplazadas/endurecidas

- SOCIAL_01: reemplazado el fallback periodístico de Primera Fuente por PDF oficial UCA/Observatorio de la Deuda Social Argentina, `OBSERVATORIO-INF_SUBSISTENCIA_WEB.pdf`, publicado el 05/12/2024.
- INST_01: reemplazada la fuente Diagonales por fuente oficial de Cámara de Diputados del 11/09/2024 sobre el veto jubilatorio.
- INST_02: agregado Chequeado como supporting para corroborar conteo 153 a favor de insistir, 87 en contra y 8 abstenciones.

## Fuentes excluidas del input

- BA Times approval/jobs: excluida porque la página figura como 8 de julio de 2025.
- BCRA REM enero 2025: excluido porque fue publicado el 06/02/2025.
- INDEC IPC enero 2025: excluido porque fue publicado en febrero 2025.
- Resultados legislativos 2025 / Wikipedia live / crónicas post-elección: ground truth directo.
- Informes BBVA/IMF/BCRA posteriores al 31/01/2025: post-corte.
- Primera Fuente/UCA fallback: excluida porque fue reemplazada por PDF oficial UCA.
- Diagonales veto 87: excluida porque fue reemplazada por fuente oficial Diputados y supporting Chequeado.
- Landing pages dinámicas de BCRA, FMI, World Bank o Wikipedia live: riesgo de actualización post-corte.

## Comandos usados para descargar/verificar

Las descargas y verificaciones fueron ejecutadas desde Python con `urllib.request` y hashes SHA256 con `hashlib.sha256`. Script usado para endurecer SOCIAL_01/INST_01:

```bash
python /tmp/harden_s1_social_inst.py
```

Ver `fetch_log.json` para URLs, HTTP status, content-type, bytes y destino local. Ver `hashes.json` para SHA256 de cada archivo local.

No se debe permitir que MiroFish acceda a URLs live durante S1; las fuentes quedan congeladas como archivos locales.

## Estado final

LISTO PARA S1.

SOCIAL_01 e INST_01 ya no dependen de fallbacks periodísticos débiles:
1. SOCIAL_01 usa PDF oficial UCA/ODSA.
2. INST_01 usa fuente oficial de Diputados.
3. INST_02 queda como supporting independiente para el conteo exacto.
