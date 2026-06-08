# Objetivo general del proyecto

Construir un benchmark piloto para evaluar MiroFish como motor de simulacion predictiva multiagente bajo control temporal estricto.

El proyecto busca medir si MiroFish puede generar predicciones utiles a partir de documentos disponibles solo hasta una fecha de corte `x`, sin acceso al resultado real ni a informacion posterior. La evaluacion debe distinguir entre dos capacidades complementarias:

1. **Backtesting objetivo:** casos con resultado claro y verificable, donde la salida pueda evaluarse como acierto/fallo o con una metrica simple.
2. **Evaluacion cualitativa/interpretable:** casos donde no hay una unica respuesta binaria, y se debe evaluar plausibilidad, cobertura, especificidad, consistencia causal, uso de evidencia, ausencia de informacion posterior y utilidad analitica.

El objetivo final no es solo comprobar si MiroFish "acierta", sino entender:

- que tan bien usa la evidencia disponible antes del corte;
- si evita filtrar informacion futura;
- si produce razonamientos causales coherentes;
- si sus predicciones son reproducibles y auditables;
- como cambia su desempeno segun el tipo de caso, corpus, horizonte temporal y configuracion de simulacion.

Todo caso debe dejar evidencia trazable:

- ficha del caso;
- fecha de corte `x`;
- distancia temporal `delta`;
- documentos de entrada permitidos;
- pregunta/prompt usado;
- output guardado de MiroFish;
- resultado real separado del input;
- evaluacion inicial documentada.

El sprint apunta a producir una base minima pero solida para comparar MiroFish en escenarios predictivos: uno mas limpio y objetivo, y otro mas cualitativo e interpretable.
