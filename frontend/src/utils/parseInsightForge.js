const LABELS = {
  query: ['分析问题', 'Analysis question', 'Pregunta de análisis'],
  scenario: ['预测场景', 'Prediction scenario', 'Escenario de predicción'],
  facts: ['相关预测事实', 'Related facts', 'Hechos relacionados'],
  entities: ['涉及实体', 'Entities involved', 'Entidades involucradas'],
  relationships: ['关系链', 'Relationship chains', 'Cadenas de relaciones'],
  subQueries: ['分析的子问题', 'Sub-questions analyzed', 'Sub-preguntas analizadas'],
  factSections: ['【关键事实】', '[Key facts]', '[Hechos clave]'],
  entitySections: ['【核心实体】', '[Core entities]', '[Entidades clave]'],
  relationSections: ['【关系链】', '[Relationship chains]', '[Cadenas de relaciones]'],
  summary: ['摘要', 'Summary', 'Resumen'],
  relatedFacts: ['相关事实', 'Related facts', 'Hechos relacionados']
}

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const alternatives = (values) => values.map(escapeRegex).join('|')

const matchLabelValue = (text, labels) => {
  const match = text.match(new RegExp(`(?:${alternatives(labels)}):\\s*(.+?)(?:\\n|$)`, 'i'))
  return match ? match[1].trim() : ''
}

const matchCount = (text, labels) => {
  const match = text.match(new RegExp(`(?:${alternatives(labels)}):\\s*(\\d+)`, 'i'))
  return match ? Number.parseInt(match[1], 10) : 0
}

const matchSection = (text, headings) => {
  const match = text.match(new RegExp(`###\\s+(?:${alternatives(headings)})[^\\n]*\\n([\\s\\S]*?)(?=\\n###|$)`, 'i'))
  return match ? match[1] : ''
}

export const parseInsightForge = (text = '') => {
  const result = {
    query: matchLabelValue(text, LABELS.query),
    simulationRequirement: matchLabelValue(text, LABELS.scenario),
    stats: {
      facts: matchCount(text, LABELS.facts),
      entities: matchCount(text, LABELS.entities),
      relationships: matchCount(text, LABELS.relationships)
    },
    subQueries: [],
    facts: [],
    entities: [],
    relations: []
  }

  const subQueries = matchSection(text, LABELS.subQueries)
  result.subQueries = subQueries
    .split('\n')
    .filter(line => /^\d+\./.test(line))
    .map(line => line.replace(/^\d+\.\s*/, '').trim())
    .filter(Boolean)

  const facts = matchSection(text, LABELS.factSections)
  result.facts = facts
    .split('\n')
    .filter(line => /^\d+\./.test(line))
    .map(line => line.replace(/^\d+\.\s*/, '').replace(/^"|"$/g, '').trim())
    .filter(Boolean)

  const entities = matchSection(text, LABELS.entitySections)
  result.entities = entities
    .split(/\n(?=- \*\*)/)
    .filter(block => block.trim().startsWith('- **'))
    .map(block => {
      const name = block.match(/^-\s*\*\*(.+?)\*\*\s*\((.+?)\)/)
      const summary = matchLabelValue(block, LABELS.summary).replace(/^"|"$/g, '')
      return {
        name: name?.[1]?.trim() || '',
        type: name?.[2]?.trim() || '',
        summary,
        relatedFactsCount: matchCount(block, LABELS.relatedFacts)
      }
    })
    .filter(entity => entity.name)

  const relations = matchSection(text, LABELS.relationSections)
  result.relations = relations
    .split('\n')
    .map(line => line.match(/^-\s*(.+?)\s*--\[(.+?)\]-->\s*(.+)$/))
    .filter(Boolean)
    .map(match => ({
      source: match[1].trim(),
      relation: match[2].trim(),
      target: match[3].trim()
    }))

  return result
}
