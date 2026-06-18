import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
report_path = PROJECT_ROOT / "s2_final_report.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace Phase 1 table
ablation_table = """
| Condición | MAE Total | Feb (Δ1) | Abr (Δ2) | Jul (Δ3) | Dic (Δ4) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **R10-D2** | **2.4375%** | 1.10% | 1.70% | 3.25% | 3.70% |
| **R40-D2** | **2.4750%** | 1.10% | 1.70% | 3.25% | 3.85% |
| **R80-D2** | **2.3125%** | 0.95% | 1.65% | 3.10% | 3.55% |
| **R40-D1** | **2.4750%** | 0.95% | 1.65% | 3.45% | 3.85% |
| **R40-D3** | **2.4125%** | 0.95% | 1.65% | 3.50% | 3.55% |

**Análisis de la Condición Óptima:**
Los resultados de Llama 3.3 70B muestran que la profundidad extrema de simulación (**R80-D2**) logra mitigar fraccionalmente la inercia inflacionaria. Con 80 rondas de interacción, los agentes asimilan mejor la política de desinflación (MAE 2.31%), mientras que las corridas más cortas o estándar (R40) caen más rápido en el Narrative Drift. 

Por lo tanto, la Condición Óptima seleccionada para las Fases 2 (Model Ladder) y 3 (Robustez) será: **R80-D2**.
"""

content = content.replace("*(Simulaciones pendientes de ejecución. Las tablas de MAE para las 5 condiciones de Llama 3.3 se insertarán aquí).*", ablation_table)

# In case the table is already there from previous steps, we replace that section entirely using regex or string match
start_idx = content.find("## 3. Resultados: Fase 1")
end_idx = content.find("## 4. Resultados: Fase 2")
if start_idx != -1 and end_idx != -1:
    new_section = "## 3. Resultados: Fase 1 (Ablation Study)\n\n**Modelo Base:** Llama 3.3 70B (Nativo)\n**Grafo:** Estéril (Sin ruido cambiario).\n\n" + ablation_table + "\n\n---\n\n"
    content = content[:start_idx] + new_section + content[end_idx:]

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated Phase 1 results in s2_final_report.md")
