# Evaluator packet — PILOT-ARG-2025-Q1

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
