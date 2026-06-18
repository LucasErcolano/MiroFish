# Seed Bundle S1 — Argentina 2025 pre-cutoff

Case ID: PILOT-ARG-2025-Q1
Cutoff exacto: 2025-01-31 23:59 Argentina local time.
Regla: este bundle resume solo fuentes publicadas hasta el cutoff. No incluye resultados electorales 2025, IPC enero 2025, REM enero 2025 ni informes macro posteriores al 31/01/2025.

## 1. Macro / inflación

Argentina entra a 2025 con una desinflación marcada pero todavía frágil. El último dato oficial disponible antes del corte es el IPC de diciembre de 2024: 2,7% mensual y 117,8% acumulado anual [MACRO_02]. Ese dato funciona como punto de partida de la simulación; cualquier inflación de enero 2025 o posterior queda fuera del input.

Las expectativas privadas e institucionales pre-corte muestran recuperación real de actividad y fuerte desaceleración inflacionaria, pero con incertidumbre por tipo de cambio, reservas y salida del cepo. BBVA proyecta un escenario de recuperación y desinflación condicionado por la continuidad del ajuste y por el manejo cambiario [MACRO_01]. El REM diciembre 2024, publicado el 07/01/2025, fija una expectativa de mercado de crecimiento 2025 alrededor de 4,5% e inflación 2025 alrededor de 25,9% [MACRO_03]. El World Bank, como fuente externa de apoyo, proyecta rebote de Argentina de 5% en 2025 y 4,7% en 2026 dentro del contexto regional [MACRO_04].

## 2. Régimen monetario / BCRA

La fuente monetaria central es el anuncio oficial del BCRA del 16/01/2025: desde el 01/02/2025 el crawling peg del tipo de cambio oficial pasa a 1% mensual [MONETARY_01]. Esta decisión refuerza el tipo de cambio como ancla nominal y debe modelarse como trade-off: ayuda a la desinflación de transables, pero profundiza el riesgo de apreciación real y presión sobre exportadores/reservas.

El Informe Monetario Mensual de diciembre 2024 agrega la foto de liquidez, base monetaria, pasivos remunerados/LEFI, crédito privado y condiciones bancarias al cierre de 2024 [MONETARY_02]. Estos datos permiten inicializar agentes financieros y de BCRA sin recurrir a informes posteriores.

## 3. Fiscal

El cierre fiscal 2024 es un pilar de la narrativa y de la restricción de política. MECON informó el 17/01/2025 que el Sector Público Nacional registró superávit financiero anual por primera vez desde 2010 [FISCAL_01]. Para la simulación, esto configura el “fiscal anchor”: el Ejecutivo tiene credibilidad de estabilización, pero también queda políticamente obligado a defender el déficit cero.

La relación causal clave es: superávit fiscal -> confianza de mercado y desinflación; pero ajuste de gasto -> estrés social, provincial y legislativo. Por eso el fiscal anchor debe interactuar con pobreza, Congreso y opinión pública, no tratarse como variable puramente técnica [FISCAL_01; SOCIAL_01; INST_01].

## 4. Política / Congreso

La elección legislativa de octubre 2025 es, desde la perspectiva pre-corte, un test de gobernabilidad para Milei y LLA. Americas Quarterly en enero 2025 enmarca la elección como punto de validación política de la agenda económica, con implicancias para FMI, geopolítica y capacidad legislativa [POL_01].

El Congreso debe modelarse como restricción institucional severa. La fuente principal para el episodio del veto jubilatorio ahora es oficial: Diputados informó el 11/09/2024 que la votación para insistir contra el veto obtuvo 153 votos positivos, 87 negativos y 8 abstenciones, sin alcanzar los dos tercios requeridos [INST_01]. Chequeado se conserva como supporting para corroborar el conteo exacto y explicar la regla de dos tercios [INST_02]. Para MiroFish, esto inicializa un “veto shield”: el Ejecutivo puede sostener vetos si conserva una coalición de bloqueo de al menos un tercio de los presentes, pero esa coalición depende de aliados y negociaciones.

## 5. Opinión pública / social

El seed pack separa aprobación electoral de bienestar material. CB Consultora diciembre 2024 aporta una medición pre-corte de opinión pública y percepción de economía del hogar [POLL_01]. La hipótesis a testear por MiroFish es si la aprobación resistente y el rechazo a alternativas previas compensan el deterioro material.

La fuente social principal fue endurecida: SOCIAL_01 ahora es PDF oficial de UCA/Observatorio de la Deuda Social Argentina, publicado el 05/12/2024, no una nota periodística. El informe registra pobreza de 49,9% en 3°T2024 y otros indicadores de subsistencia/privaciones, funcionando como contrapeso social al optimismo macro [SOCIAL_01]. Para S1, su función es inicializar estrés social, riesgo de protesta, sensibilidad al empleo/salarios y oportunidad opositora.

## 6. FMI / geopolítica

El IMF Ex-post Evaluation publicado el 10/01/2025 fija el marco externo: sostenibilidad del programa, necesidad de normalizar el régimen cambiario, reservas, tasas reales y costo social del ajuste [GEO_01]. Americas Quarterly complementa con el contexto geopolítico de alineamiento con Estados Unidos, relación pragmática con China y relevancia del FMI para la estabilización [POL_01].

Para MiroFish, el FMI no debe modelarse como simple financista, sino como agente/constraint: su apoyo puede aliviar reservas, pero sus condiciones empujan hacia salida del cepo, mayor flexibilidad cambiaria y consistencia monetaria [GEO_01].

## 7. Riesgos persistentes a simular

- Inflación: tendencia descendente pre-corte, pero vulnerable a corrección cambiaria y tarifas [MACRO_01; MACRO_02; MACRO_03].
- Cepo / reservas: la salida del cepo es necesaria para inversión y normalización, pero puede generar devaluación e inflación si reservas son insuficientes [GEO_01; MONETARY_01].
- Crawling peg: el 1% mensual ancla expectativas, pero puede apreciar el tipo de cambio real y afectar exportadores [MONETARY_01].
- Fiscal anchor: superávit fortalece credibilidad, pero limita margen para responder a pobreza, provincias y Congreso [FISCAL_01; SOCIAL_01; INST_01].
- Congreso: el Ejecutivo depende de sostener más de un tercio para proteger vetos y evitar leyes que rompan el equilibrio fiscal [INST_01; INST_02].
- Opinión pública: aprobación y tolerancia al ajuste pueden sostenerse si la desinflación y recuperación se perciben, pero pobreza/empleo/salarios pueden erosionarla [POLL_01; SOCIAL_01].
- Geopolítica/FMI: apoyo externo puede ser decisivo para reservas y confianza, pero también aumenta restricciones de política [GEO_01; POL_01].
