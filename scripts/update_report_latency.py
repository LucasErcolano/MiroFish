import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
report_path = PROJECT_ROOT / "s2_final_report.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

ablation_table = """
| Condición | MAE Total | Feb (Δ1) | Abr (Δ2) | Jul (Δ3) | Dic (Δ4) | Latencia (seg) | Costo Est. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **R10-D2** | **2.4375%** | 1.10% | 1.70% | 3.25% | 3.70% | ~247s | $0.02 |
| **R40-D2** | **2.4750%** | 1.10% | 1.70% | 3.25% | 3.85% | ~674s | $0.08 |
| **R80-D2** | **2.3125%** | 0.95% | 1.65% | 3.10% | 3.55% | ~923s | $0.17 |
| **R40-D1** | **2.4750%** | 0.95% | 1.65% | 3.45% | 3.85% | ~338s | $0.08 |
| **R40-D3** | **2.4125%** | 0.95% | 1.65% | 3.50% | 3.55% | ~309s | $0.08 |

**Aclaración Metodológica (Línea 5 - Variante B):**
Para el estudio de profundidad (R10 vs R40 vs R80), la arquitectura de MiroFish implementó la **Variante B (Más duración simulada)**. Se mantuvo constante la resolución temporal (`minutes_per_round = 60`), lo que significa que R10 simuló 10 horas de interacciones, R40 simuló 40 horas, y R80 simuló 80 horas de exposición narrativa de los agentes.

**Análisis de la Condición Óptima (Profundidad vs. Latencia):**
Los resultados de Llama 3.3 70B muestran que la profundidad extrema de simulación (**R80-D2**) logra mitigar fraccionalmente la inercia inflacionaria, bajando el MAE a 2.31%. Sin embargo, la latencia escala de forma casi lineal: R80 (923s) tarda casi cuatro veces más que R10 (247s). A pesar del incremento en tiempo de cómputo y costo, seleccionamos R80-D2 como la "Condición Óptima" para el resto de las Fases para maximizar la inmersión narrativa antes de inyectar el ruido.
"""

# Replace the existing Phase 1 table
start_idx = content.find("| Condición | MAE Total | Feb")
end_idx = content.find("---", start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + ablation_table + "\n\n" + content[end_idx:]

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Report updated with Latency, Cost, and Variant B explanation.")
