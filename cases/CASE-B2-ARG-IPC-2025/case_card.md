# CASE-B2-ARG-IPC-2025

Dominio: inflación mensual argentina (IPC INDEC).

Fecha de corte x: 2025-01-31.

Horizonte Δ:
- Δ1: 1 mes — febrero 2025
- Δ2: 3 meses — abril 2025
- Δ3: 6 meses — julio 2025
- Δ4: 11 meses — diciembre 2025

Pregunta central:
Usando exclusivamente documentos fechados hasta el 31 de enero de 2025, predecir la variación mensual del IPC en Argentina para cada horizonte. Evalúa si el sistema puede modelar la trayectoria de desinflación bajo el programa de Milei a partir de señales sociales y macroeconómicas disponibles antes de x.

Input: reusar input_pack_pre_x/ de PILOT-ARG-2025-Q1 (mismos documentos).
Desenlace real: documentado solo en answer_key_post_x/.

Modelo: gemini-2.5-flash-lite vía endpoint OpenAI-compatible de Google.
