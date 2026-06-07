import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
report_path = PROJECT_ROOT / "s2_final_report.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

provenance_section = """
## 9. Trazabilidad de Datos (Data Provenance)

Para garantizar la auditabilidad total del experimento conforme al Issue #18, se detalla el mapeo entre las tablas de resultados y los directorios de salida canónicos. Cada métrica reportada puede ser reconstruida auditando los archivos `stats.json` (costo/latencia), `verdict.json` (predicciones) y `run_info.json` (configuración verificada) en las siguientes rutas:

### **Matriz de Ablación (Fase 1)**
| Condición | Directorio Canónico (`runs/s2/`) |
| :--- | :--- |
| **R10-D2** | `R10-D2_Llama-3.3-70B-Instruct` |
| **R40-D2** | `R40-D2_Llama-3.3-70B-Instruct` |
| **R80-D2** | `R80-D2_Llama-3.3-70B-Instruct` |
| **R40-D1** | `R40-D1_Llama-3.3-70B-Instruct` |
| **R40-D3** | `R40-D3_Llama-3.3-70B-Instruct` |

### **Model Ladder (Fase 2)**
| Modelo | Directorio Canónico (`runs/s2/`) |
| :--- | :--- |
| **Llama 3.3 70B** | `R80-D2_Llama-3.3-70B-Instruct` |
| **Gemma 3 27B IT** | `R80-D2_gemma-3-27b-it` |
| **Qwen3 8B** | `R80-D2_qwen3-8b` |

### **Robustez y Réplicas (Fase 3)**
| Réplica | Directorio Canónico (`runs/s2/`) |
| :--- | :--- |
| **Run Base** | `R80-D2_Llama-3.3-70B-Instruct` |
| **Réplica 1** | `R80-D2_Llama-3.3-70B-Instruct_rep1` |
| **Réplica 2** | `R80-D2_Llama-3.3-70B-Instruct_rep2` |
| **Réplica 3** | `R80-D2_Llama-3.3-70B-Instruct_rep3` |

### **Stress Test (Fase 4)**
| Condición | Directorio de Referencia |
| :--- | :--- |
| **Chaos Run** | `R80-D2_Llama-3.3-70B-Instruct` (Ejecutado post-contaminación del grafo) |

*Nota: Los directorios duplicados con nomenclaturas de guiones bajos (`_`) han sido purgados para mantener un único set canónico de auditoría con nomenclatura de guiones (`-`).*
"""

if "## 9. Trazabilidad de Datos" not in content:
    content += "\n" + provenance_section

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Data provenance section added for strict auditeability.")
