const ROOT_PAGE_LABELS = {
  index: 'Overview',
  agents: 'Agents',
  timeline: 'Timeline',
  sources: 'Sources',
  contradictions: 'Open Questions',
  wiki_context: 'Wiki Context',
  wiki_compile_log: 'Compile Log',
  wiki_meta: 'Metadata'
}

const KIND_LABELS = {
  root: 'Overview',
  entity: 'Entities',
  claim: 'Claims',
  meta: 'Metadata'
}

const KIND_ORDER = {
  root: 0,
  entity: 1,
  claim: 2,
  meta: 3
}

const titleCase = (value) => {
  return String(value || '')
    .replace(/\.(md|json)$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, char => char.toUpperCase())
}

const basename = (path) => String(path || '').split('/').pop() || ''
const isOpaqueId = (value) => {
  const text = String(value || '').trim()
  return /^\d+$/.test(text) || /^[0-9a-f]{8}-[0-9a-f-]{20,}$/i.test(text)
}

export const formatNumber = (value) => Number(value || 0).toLocaleString()

export const formatCost = (value) => `$${Number(value || 0).toFixed(4)}`

export const formatCostWithStatus = (value, status = 'estimated') => {
  if (status === 'unknown') return 'Not estimated'
  if (status === 'none') return 'No telemetry'
  if (status === 'partial' && Number(value || 0) === 0) return 'Partially estimated'
  if (status === 'partial') return `${formatCost(value)} est.`
  return formatCost(value)
}

export const friendlyWikiTitle = (page) => {
  const path = page?.path || ''
  const name = basename(path).replace(/\.(md|json)$/i, '')
  const directLabel = ROOT_PAGE_LABELS[name]
  if (directLabel) return directLabel

  const rawTitle = String(page?.title || '').replace(/^#\s*/, '').trim()
  if (rawTitle && rawTitle !== path && rawTitle !== name && !isOpaqueId(rawTitle)) {
    return titleCase(rawTitle)
  }

  if (path.startsWith('entities/')) return isOpaqueId(name) ? 'Entity' : titleCase(name.replace(/^entity[_-]?/i, ''))
  if (path.startsWith('claims/')) return isOpaqueId(name) ? 'Claim' : titleCase(name.replace(/^claim[_-]?/i, 'Claim '))
  return titleCase(name || path)
}

export const friendlyWikiKind = (kind) => KIND_LABELS[kind] || titleCase(kind || 'Page')

export const normalizeWikiPages = (pages = []) => {
  return [...pages]
    .map(page => ({
      ...page,
      displayTitle: friendlyWikiTitle(page),
      displayKind: friendlyWikiKind(page.kind),
      sortWeight: KIND_ORDER[page.kind] ?? 10
    }))
    .sort((a, b) => {
      if (a.sortWeight !== b.sortWeight) return a.sortWeight - b.sortWeight
      return a.displayTitle.localeCompare(b.displayTitle)
    })
}

export const summarizeTelemetry = (telemetry) => {
  const totals = telemetry?.totals || {}
  const calls = Number(totals.calls || 0)
  const tokens = Number(totals.tokens_in || 0) + Number(totals.tokens_out || 0)
  const status = totals.cost_estimation_status || (calls ? 'estimated' : 'none')
  const unknownCostCalls = Number(totals.cost_unknown_model_calls || 0)
  const usageUnavailableCalls = Number(totals.usage_unavailable_calls || 0)
  const rateLimitedCalls = Number(totals.rate_limited_calls || 0)
  const cost = Number(totals.cost_usd_est || 0)

  const costLabel = formatCostWithStatus(cost, status)

  const notices = []
  if (unknownCostCalls) notices.push(`${unknownCostCalls} calls missing model price`)
  if (usageUnavailableCalls) notices.push(`${usageUnavailableCalls} calls without usage`)
  if (rateLimitedCalls) notices.push(`${rateLimitedCalls} rate limited`)

  return {
    calls,
    errors: Number(totals.errors || 0),
    parseErrors: Number(totals.parse_errors || 0),
    tokens,
    cost,
    costLabel,
    costStatus: status,
    unknownCostCalls,
    usageUnavailableCalls,
    rateLimitedCalls,
    p95: Number(totals.latency_p95_ms || 0),
    notices,
    hasData: calls > 0
  }
}

export const summarizeRouting = (audit) => {
  const records = audit?.records || []
  const models = new Set(records.map(row => row.model).filter(Boolean))
  const providers = new Set(records.map(row => row.provider).filter(Boolean))
  return {
    records,
    total: records.length,
    modelCount: models.size,
    providerCount: providers.size,
    models: Array.from(models)
  }
}

const statusFor = ({ done, active, failed }) => {
  if (failed) return 'warning'
  if (done) return 'done'
  if (active) return 'active'
  return 'todo'
}

const stageIncludes = (stageKey, stageName, needles) => {
  const text = `${stageKey || ''} ${stageName || ''}`.toLowerCase()
  return needles.some(needle => text.includes(needle))
}

const compactText = (value, max = 240) => {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max - 1)}...` : text
}

export const firstReadableLines = (value, maxLines = 3) => {
  return String(value || '')
    .split(/\n+/)
    .map(line => line.replace(/^[-*#>\d.\s]+/, '').trim())
    .filter(line => {
      if (line.length <= 24) return false
      if (/^AUTONOMOUS DEEP SEARCH/i.test(line)) return false
      if (/^Simulation Prompt/i.test(line)) return false
      if (/^Report focus/i.test(line)) return false
      if (/^Run a compact/i.test(line)) return false
      if (/^Use semantic deduplication/i.test(line)) return false
      if (/^Preserve contradictions/i.test(line)) return false
      if (/^Generate wiki/i.test(line)) return false
      if (/^Route different roles/i.test(line)) return false
      if (/^Make telemetry useful/i.test(line)) return false
      if (/^Produce a final/i.test(line)) return false
      return true
    })
    .slice(0, maxLines)
}

export const extractResearchBody = (content) => {
  const text = String(content || '').trim()
  if (!text) return ''

  const markdownStart = text.search(/\n##\s+/)
  if (markdownStart >= 0) {
    return text.slice(markdownStart).trim()
  }

  const separator = text.match(/\n\s*---\s*\n/)
  if (separator?.index != null) {
    return text.slice(separator.index + separator[0].length).trim()
  }

  return text.replace(/^---\s*AUTONOMOUS DEEP SEARCH[\s\S]*?---\s*/i, '').trim()
}

export const buildPreparationMilestones = ({
  stageKey,
  stageName,
  profileCount,
  expectedTotal,
  candidateTotal,
  profiles = [],
  simulationConfig = null,
  hasConfig,
  wiki,
  deepSearch,
  deduplication
}) => {
  const pages = wiki?.pages || []
  const dedupSummary = deduplication?.summary
  const dedupFailed = dedupSummary?.status === 'failed'
  const profilesDone = Boolean(expectedTotal && profileCount >= expectedTotal)
  const researchLines = firstReadableLines(extractResearchBody(deepSearch?.content))
  const configTime = simulationConfig?.time_config || {}
  const configEvents = simulationConfig?.event_config || {}
  const platforms = [
    simulationConfig?.twitter_config ? 'Plaza' : null,
    simulationConfig?.reddit_config ? 'Community' : null
  ].filter(Boolean)
  const rounds = configTime.total_simulation_hours && configTime.minutes_per_round
    ? Math.floor((configTime.total_simulation_hours * 60) / configTime.minutes_per_round)
    : null

  return [
    {
      key: 'research',
      label: 'Deep Research',
      detail: deepSearch?.available ? 'New context found' : 'Collecting external context',
      summary: researchLines.length
        ? researchLines.join(' ')
        : (deepSearch?.available ? compactText(deepSearch.content) : 'Looking for external context that can shape agents, market claims, and scenario rules.'),
      meta: deepSearch?.available ? [
        { label: 'Trace', value: 'Saved' },
        { label: 'Findings', value: researchLines.length || 1 }
      ] : [
        { label: 'Context', value: stageIncludes(stageKey, stageName, ['research', 'deep']) ? 'Collecting' : 'Pending' }
      ],
      status: statusFor({
        done: Boolean(deepSearch?.available),
        active: stageIncludes(stageKey, stageName, ['research', 'deep'])
      })
    },
    {
      key: 'dedup',
      label: 'Deduplication',
      detail: dedupSummary
        ? `${dedupSummary.before_entities ?? 0} -> ${dedupSummary.after_entities ?? 0} agents`
        : 'Merging repeated entities',
      summary: dedupSummary
        ? `${dedupSummary.removed_entities ?? 0} duplicate or overlapping agent candidates removed before profiles are generated. The graph itself is not rewritten.`
        : `${candidateTotal || 0} agent candidates from the graph will be checked before final profiles are created.`,
      meta: dedupSummary ? [
        { label: 'Before', value: dedupSummary.before_entities ?? '-' },
        { label: 'After', value: dedupSummary.after_entities ?? '-' },
        { label: 'Removed', value: dedupSummary.removed_entities ?? 0 },
        { label: 'Threshold', value: dedupSummary.threshold ?? '-' }
      ] : [
        { label: 'Agent candidates', value: candidateTotal || '-' }
      ],
      status: statusFor({
        done: Boolean(dedupSummary) && !dedupFailed,
        active: stageIncludes(stageKey, stageName, ['dedup']),
        failed: dedupFailed
      })
    },
    {
      key: 'wiki',
      label: 'Wiki',
      detail: pages.length ? `${pages.length} pages compiled` : 'Preparing reusable context',
      summary: pages.length
        ? 'The Wiki is ready as the readable evidence layer for report generation and review.'
        : 'Wiki pages will be compiled after the final agent set is available.',
      meta: pages.length ? [
        { label: 'Pages', value: pages.length },
        { label: 'Entities', value: pages.filter(page => page.kind === 'entity').length },
        { label: 'Claims', value: pages.filter(page => page.kind === 'claim').length }
      ] : [],
      status: statusFor({
        done: pages.length > 0,
        active: stageIncludes(stageKey, stageName, ['wiki', 'compile'])
      })
    },
    {
      key: 'profiles',
      label: 'Agent Profiles',
      detail: `${profileCount || 0}/${expectedTotal || '?'} generated`,
      summary: profiles.length
        ? profiles.slice(0, 3).map(profile => profile.username || profile.name || 'Agent').join(', ')
        : 'Final deduplicated entities become agents with roles, bios, interests and behavior context.',
      meta: [
        { label: 'Generated', value: profileCount || 0 },
        { label: 'Expected', value: expectedTotal || '-' },
        { label: 'Candidates', value: candidateTotal || '-' }
      ],
      status: statusFor({
        done: profilesDone,
        active: stageIncludes(stageKey, stageName, ['profile', 'agent', '人设'])
      })
    },
    {
      key: 'config',
      label: 'Simulation Config',
      detail: hasConfig ? 'Simulation rules ready' : 'Generating behavior rules',
      summary: hasConfig
        ? compactText(configEvents.narrative_direction || 'Runtime behavior, schedule and initial posts are ready.')
        : 'The system is preparing platform rules, timing and initial conversation seeds.',
      meta: hasConfig ? [
        { label: 'Platforms', value: platforms.length ? platforms.join(' + ') : '-' },
        { label: 'Rounds', value: rounds || '-' },
        { label: 'Posts', value: configEvents.initial_posts?.length || 0 }
      ] : [],
      status: statusFor({
        done: Boolean(hasConfig),
        active: stageIncludes(stageKey, stageName, ['config', '配置'])
      })
    }
  ]
}

export const buildEvidenceSteps = ({ wiki, telemetry, audit, deepSearch, deduplication, verdicts }) => {
  const telemetrySummary = summarizeTelemetry(telemetry)
  const routingSummary = summarizeRouting(audit)
  const wikiPages = wiki?.pages || []
  const dedupSummary = deduplication?.summary
  return [
    {
      key: 'deep',
      label: 'Deep Research',
      value: deepSearch?.available ? 'Trace saved' : 'Waiting',
      status: deepSearch?.available ? 'done' : 'todo'
    },
    {
      key: 'dedup',
      label: 'Deduplication',
      value: dedupSummary ? `${dedupSummary.removed_entities ?? 0} merged` : 'Waiting',
      status: dedupSummary?.status === 'failed' ? 'warning' : (dedupSummary ? 'done' : 'todo')
    },
    {
      key: 'wiki',
      label: 'Wiki',
      value: wikiPages.length ? `${wikiPages.length} pages` : 'Waiting',
      status: wikiPages.length ? 'done' : 'todo'
    },
    {
      key: 'telemetry',
      label: 'Telemetry',
      value: telemetrySummary.hasData ? `${telemetrySummary.calls} calls` : 'Waiting',
      status: ['unknown', 'partial'].includes(telemetrySummary.costStatus) ? 'warning' : (telemetrySummary.hasData ? 'done' : 'todo')
    },
    {
      key: 'routing',
      label: 'Routing',
      value: routingSummary.total ? `${routingSummary.modelCount} models` : 'Waiting',
      status: routingSummary.total ? 'done' : 'todo'
    },
    {
      key: 'fusion',
      label: 'Fusion',
      value: verdicts?.length ? `${verdicts.length} verdicts` : 'Waiting',
      status: verdicts?.length ? 'done' : 'todo'
    }
  ]
}
