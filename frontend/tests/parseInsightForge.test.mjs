import test from 'node:test'
import assert from 'node:assert/strict'

import { parseInsightForge } from '../src/utils/parseInsightForge.js'


test('parses localized English InsightForge output', () => {
  const result = parseInsightForge(`## Deep predictive analysis
Analysis question: Match outcome
Prediction scenario: Pre-match evidence only

### Data statistics
- Related facts: 2
- Entities involved: 1
- Relationship chains: 1

### Sub-questions analyzed
1. Which side has the advantage?

### [Key facts] (quote these verbatim in the report)
1. "Argentina has experience."
2. "Colombia has momentum."

### [Core entities]
- **Argentina** (Team)
  Summary: "Defending champion"
  Related facts: 1

### [Relationship chains]
- Argentina --[faces]--> Colombia`)

  assert.deepEqual(result.stats, { facts: 2, entities: 1, relationships: 1 })
  assert.deepEqual(result.facts, ['Argentina has experience.', 'Colombia has momentum.'])
  assert.equal(result.entities[0].name, 'Argentina')
  assert.deepEqual(result.relations[0], { source: 'Argentina', relation: 'faces', target: 'Colombia' })
})

test('parses localized Spanish InsightForge output', () => {
  const result = parseInsightForge(`## Análisis predictivo profundo
Pregunta de análisis: Resultado del partido
Escenario de predicción: Solo evidencia previa

### Estadísticas de datos
- Hechos relacionados: 1
- Entidades involucradas: 0
- Cadenas de relaciones: 0

### Sub-preguntas analizadas
1. ¿Quién tiene ventaja?

### [Hechos clave] (cita estos textos originales en el informe)
1. "Argentina tiene experiencia."`)

  assert.equal(result.query, 'Resultado del partido')
  assert.equal(result.stats.facts, 1)
  assert.deepEqual(result.facts, ['Argentina tiene experiencia.'])
})
