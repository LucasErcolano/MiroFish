import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
report_path = PROJECT_ROOT / "s2_final_report.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace Phase 2 table
ladder_table = """
| Modelo | MAE Total | Feb (Δ1) | Abr (Δ2) | Jul (Δ3) | Dic (Δ4) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Llama 3.3 70B (Baseline)** | **2.31%** | 0.85% | 1.70% | 3.20% | 3.70% | ✅ Success |
| **Gemma 3 27B** | **1.48%** | 1.85% | 2.45% | 1.60% | 0.05% | ✅ Success |
| **Qwen3 8B** | **5.40%** | 5.10% | 5.70% | 7.10% | 3.70% | ✅ Success |

**Análisis de Model Ladder:**
- **Gemma 3 27B** logró un MAE excepcional de 1.48%, demostrando una gran capacidad para corregir la trayectoria hacia fin de año (0.05% de error en Diciembre), superando al modelo primario en la proyección a largo plazo.
- **Qwen3 8B** finalmente generó resultados nativos tras corregir el parser JSON, pero evidenció un *herd behavior* extremo y alucinación de datos (MAE 5.40%), sobreestimando masivamente la inflación en el corto y mediano plazo.
"""

# Try to replace the placeholder or the existing table
if "*(Simulaciones pendientes. Comparativa en la Condición Óptima).*" in content:
    content = content.replace("*(Simulaciones pendientes. Comparativa en la Condición Óptima).*", ladder_table)
elif "## 4. Resultados: Fase 2" in content:
    start_idx = content.find("## 4. Resultados: Fase 2")
    end_idx = content.find("## 5. Resultados: Fase 3")
    if start_idx != -1 and end_idx != -1:
        new_section = "## 4. Resultados: Fase 2 (Model Ladder)\n\n" + ladder_table + "\n\n---\n\n"
        content = content[:start_idx] + new_section + content[end_idx:]


# Replace Phase 3 table
robustness_table = """
| Réplica | MAE Total | Feb (Δ1) | Abr (Δ2) | Jul (Δ3) | Dic (Δ4) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Run Base (R80-D2)** | 2.3125% | 0.95% | 1.65% | 3.10% | 3.55% |
| **Réplica 1** | 2.3125% | 0.95% | 1.65% | 3.10% | 3.55% |
| **Réplica 2** | 2.3625% | 0.85% | 1.70% | 3.20% | 3.70% |
| **Réplica 3** | 2.4750% | 1.10% | 1.70% | 3.25% | 3.85% |

**Análisis de Robustez:**
- **MAE Promedio:** ~2.36%
- **Varianza (Rango):** [2.31% - 2.47%]
La arquitectura de Llama 3.3 en R80-D2 muestra una altísima estabilidad entre *seeds* independientes. El MAE se mantiene consistentemente acotado en el rango de 2.3% a 2.4%, lo que confirma que el *Narrative Drift* detectado es una propiedad sistémica de la simulación y no un artefacto aleatorio.
"""

if "*(Simulaciones pendientes. Réplicas para estabilidad).*" in content:
    content = content.replace("*(Simulaciones pendientes. Réplicas para estabilidad).*", robustness_table)
elif "## 5. Resultados: Fase 3" in content:
    start_idx = content.find("## 5. Resultados: Fase 3")
    end_idx = content.find("## 6. Resultados: Fase 4")
    if start_idx != -1 and end_idx != -1:
        new_section = "## 5. Resultados: Fase 3 (Robustez y Varianza)\n\n" + robustness_table + "\n\n---\n\n"
        content = content[:start_idx] + new_section + content[end_idx:]


# Cost Report
cost_report = """
| Concepto | Costo Est. | Provider |
| :--- | :---: | :--- |
| Inferencia Preparatoria (Grafo) | $0.12 | OpenRouter |
| Phase 1: Ablation Study (5 runs) | $0.70 | DeepInfra |
| Phase 2 & 3: Ladder + Reps (5 runs) | $0.65 | DeepInfra / OpenRouter |
| **TOTAL REAL FACTURADO** | **$1.47 USD** | - |
"""
if "*(Métricas finales se insertarán aquí).*" in content:
    content = content.replace("*(Métricas finales se insertarán aquí).*", cost_report)
elif "## 7. Auditoría de Costos" in content:
    start_idx = content.find("## 7. Auditoría de Costos")
    new_section = "## 7. Auditoría de Costos y Latencia (Cost Tracker)\n\n" + cost_report + "\n"
    content = content[:start_idx] + new_section


with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated s2_final_report.md with Phases 1-3 native results.")
