# Ground Truth Private

No incluir este archivo como input de MiroFish.

## Resultado

- Evento: balotaje presidencial de Bolivia 2025.
- Fecha: 2025-10-19.
- Ganador real: Rodrigo Paz.
- Rival principal: Jorge "Tuto" Quiroga.

## Resultado cuantitativo de referencia

Usar estos valores como ground truth operativo para la metrica secundaria. Si luego se decide usar el computo oficial definitivo con otra agregacion, actualizar todos los valores en bloque y dejar nota de version.

- Rodrigo Paz: 54.53
- Jorge Quiroga: 45.47
- Otros / blanco / nulo: 0.00
- Margen Paz - Quiroga: 9.06 puntos

## Metrica primaria

- `correcto`: el reporte predice `Paz gana` o equivalente claro.
- `incorrecto`: el reporte predice `Quiroga gana`, empate/no evaluable u otro ganador.

## Metricas secundarias

- `mae_vote_share`: error absoluto medio para Paz, Quiroga y otros/blanco/nulo.
- `margin_abs_error`: error absoluto del margen Paz - Quiroga.
- `parsed_vote_shares`: porcentajes extraidos del reporte.

## Fuentes de verificacion posterior

- El Pais: resultado preliminar con Rodrigo Paz ganador.
- AP/PBS: Rodrigo Paz gana el balotaje y termina el ciclo de dominio del MAS.
- Tribunal Supremo Electoral de Bolivia: computo oficial.
