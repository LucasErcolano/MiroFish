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

## Complexity Gate (Aprobado S2)
- **Documentos Seed:** 13 documentos
- **Fechas documentales distintas:** > 3 (Cubre finales de 2024 y Enero 2025)
- **Fuentes:** Múltiples (BCRA, FMI, INDEC, BBVA, Consultoras)
- **Hipótesis Causales Competidoras:** 2 (Desinflación oficial vs. Rebote por emisión/atraso cambiario)
- **Documento Distractor/Noise:** `input_04_noise_dolar.txt` (Aislado para Grupo de Control, activo para Fase 4)
- **Entidades Extraíbles:** > 20
- **Ground Truth:** Aislado en `ground_truth.json`
- **Métrica Predefinida:** MAE (Mean Absolute Error) por cada horizonte temporal.

## Configuración de Modelos (S2)
- **Modelo Primario Fijo:** `deepinfra/meta-llama/Llama-3.3-70B-Instruct` (Cutoff: Dec 2023 - Previene Data Leakage)
- **Model Ladder (Sanity Check):** Qwen3 8B, Gemma 3 27B IT.
