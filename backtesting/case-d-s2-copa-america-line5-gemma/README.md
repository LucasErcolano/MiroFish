# Case D S2 Copa America Line 5 Gemma

Caso temporal acumulativo basado en el setup de Issue #19, pero con objetivo distinto: medir como cambia la prediccion al aumentar la profundidad de evidencia pre-cutoff.

## Pregunta

Predecir el ganador de la final Copa America 2024 entre Argentina y Colombia usando solo informacion disponible hasta el 13 de julio de 2024.

## Paquetes temporales

- `T0`: contexto minimo base tomado del packet de Issue #19.
- `T1`: T0 + resultados de semifinales y forma reciente.
- `T2`: T1 + odds/modelos/previews que favorecen a Argentina.
- `T3`: T2 + contrapeso Colombia y riesgos.

Los seeds son acumulativos. `seed_T1.md` contiene T0 + T1; `seed_T2.md` contiene T0 + T1 + T2; `seed_T3.md` contiene todo lo anterior + T3.

## Diferencia con Issue #19

Issue #19 probo sensibilidad posicional y ruido con inyecciones durante la simulacion. Este caso no busca replicar ruido ni timing de inyeccion. Usa el mismo tipo de pregunta/salida, pero reorganiza la evidencia como paquetes acumulativos `T0/T1/T2/T3`.

## Correr

Backend requerido en `http://127.0.0.1:5001`.

```bash
python3 backtesting/case-d-s2-copa-america-line5-gemma/run_temporal_matrix.py --variant gemma_T0_R40_D2 --force
python3 backtesting/case-d-s2-copa-america-line5-gemma/run_temporal_matrix.py --variant gemma_T1_R40_D2 --force
python3 backtesting/case-d-s2-copa-america-line5-gemma/run_temporal_matrix.py --variant gemma_T2_R40_D2 --force
python3 backtesting/case-d-s2-copa-america-line5-gemma/run_temporal_matrix.py --variant gemma_T3_R40_D2 --force
```

Outputs esperados por variante:

- `structured_answer.json`
- `eval_result.json`
- `worldbuilding_trace.json`
- `worldbuilding_artifacts/`
- `simulation_config.json`
- `state.json`
- `run_state.json`
- `report.md`
- `run_notes.md`
