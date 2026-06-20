# Quality audit pre-run — PILOT-ARG-2025-Q1

Date: 2026-05-21
Scope: opción 3, sin ejecutar MiroFish. Auditoría del paquete experimental, no evaluación de predicción.

## 1. Separación temporal

Estado: PASS.

Evidencia:
- `input_pack_pre_x/manifest.csv` contiene 6 fuentes con `published_date <= 2025-01-31`.
- `model_output_raw/artifacts/pre_cutoff_scan.py` no detectó strings prohibidos en `input_pack_pre_x`.
- `answer_key_post_x/` contiene los datos post-corte y está separado físicamente de `input_pack_pre_x/` y `prompt_frozen/`.

Riesgo residual:
- El escaneo de contaminación temporal es heurístico. Detecta strings obvios, no todo posible leak semántico.
- Las fuentes HTML pre-corte pueden incluir boilerplate dinámico del sitio al momento de acceso. Mitigación: se preservan extractos relevantes en `input_pack_pre_x/excerpts/` y hashes de los archivos completos.

## 2. Seed bundle

Estado: PASS con observaciones menores.

Fortalezas:
- Resume solo variables disponibles pre-corte: inflación, crawling peg, reservas, empleo/salarios, aprobación, Congreso, oposición y FMI.
- Cita source_id en cada claim narrativo.
- No incluye resultado electoral real, porcentaje de LLA, inflación final 2025 ni referencias a fuentes post-corte.
- Es suficientemente informativo para orientar causalidad sin dar el desenlace.

Observaciones:
- La frase “aprobación presidencial se mantenía competitiva” es interpretativa. Es aceptable porque está anclada en fuente de opinión pública pre-corte, pero el evaluador debe verificar si el output la sobreconvierte en predicción determinista.
- La frase “necesidad de aumentar bancas” puede orientar al modelo hacia consolidación legislativa, pero es parte de la pregunta operacional y estaba en análisis pre-corte. No se considera fuga temporal.
- El bundle no fuerza rangos numéricos de voto ni inflación 2025, lo cual preserva valor predictivo.

Decisión:
- No modificar `seed_bundle.md` para no reabrir el input congelado. Mantener hash y trazabilidad.

## 3. Prompt congelado

Estado: PASS.

Fortalezas:
- Obliga a responder con rangos, escenarios probabilísticos, mecanismos causales, riesgos y evidencia.
- Prohíbe explícitamente información posterior al 31/01/2025.
- Exige citar source_id por claim importante.

Riesgo residual:
- El prompt pide “simulá la evolución político-económica argentina durante 2025”; un modelo con conocimiento propio posterior podría filtrar datos. Mitigación: restricciones de sistema, configuración sin web/RAG/memoria y rúbrica E penalizan fugas temporales.

## 4. Rúbrica

Estado: PASS con mejora aplicada.

Fortalezas:
- Seis dimensiones separan especificidad, plausibilidad, cobertura, causalidad, temporalidad y utilidad.
- La dimensión E penaliza uso de información posterior.

Mejora aplicada:
- Se reforzó la rúbrica para indicar explícitamente que no debe premiarse exactitud si parece fuga temporal, y que la plausibilidad debe ponderar dirección/magnitud separada de causalidad.

## 5. Answer key

Estado: PASS.

Fortalezas:
- Reuters dejó de ser fuente bloqueante.
- Se agregaron fuentes accesibles equivalentes: Buenos Aires Times, AP, NPR, El País English.
- Se agregó cross-check oficial vía API de la Dirección Nacional Electoral / Ministerio del Interior (`GT7_DINE_API_2025`).

Matiz importante:
- Buenos Aires Times reporta 40,84% con 90% escrutado y AP/NPR/El País reportan “más de 40%”.
- La computación reproducible desde la API oficial para Diputado Nacional, sumando nombres que contienen `LIBERTAD AVANZA` en 24 distritos, da 40,6556% sobre votos positivos. Esto es consistente con “algo más de 40%”, pero no idéntico al 40,84% reportado por medios.
- Para evaluación, usar rango ground truth recomendado: LLA ≈ 40–41%, no exigir exactitud decimal.

## 6. Conclusión

El paquete está listo como caso experimental pendiente de corrida. La principal limitación ya no es la evidencia post-corte sino la falta del CLI `mirofish` para producir output crudo.

Estado final de auditoría: PASS / READY_WITH_BLOCKED_RUN.
