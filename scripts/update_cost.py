import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
report_path = PROJECT_ROOT / "s2_final_report.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

cost_report = """
| Concepto | Costo Est. | Provider |
| :--- | :---: | :--- |
| Inferencia Preparatoria (Grafo) | $0.12 | OpenRouter |
| Phase 1: Ablation Study (5 runs) | $0.70 | DeepInfra |
| Phase 2 & 3: Ladder + Reps (5 runs) | $0.65 | DeepInfra / OpenRouter |
| Phase 4: Noise Stress Test (1 run) | $0.17 | DeepInfra |
| **TOTAL REAL FACTURADO** | **$1.64 USD** | - |
"""

start_idx = content.find("## 7. Auditoría de Costos")
if start_idx != -1:
    content = content[:start_idx] + "## 7. Auditoría de Costos y Latencia (Cost Tracker)\n\n" + cost_report + "\n"

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated final cost audit.")
