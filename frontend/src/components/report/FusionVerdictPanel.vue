<template>
  <section class="fusion-panel" :class="{ compact }">
    <div class="fusion-header">
      <div>
        <span class="fusion-kicker">Fusion verdict</span>
        <h3>{{ title }}</h3>
      </div>
      <span class="fusion-status">{{ status }}</span>
    </div>

    <div class="fusion-grid">
      <div class="fusion-cell">
        <span>Outcome</span>
        <strong>{{ outcomeLabel }}</strong>
      </div>
      <div class="fusion-cell">
        <span>Confidence</span>
        <strong>{{ confidence }}</strong>
      </div>
      <div class="fusion-cell">
        <span>Sources</span>
        <strong>{{ sourceCount }}</strong>
      </div>
    </div>

    <p v-if="summary" class="fusion-summary">{{ summary }}</p>

    <div v-if="risks.length || recommendedChecks.length" class="fusion-lists">
      <div v-if="risks.length">
        <span class="fusion-list-title">Risks</span>
        <ul>
          <li v-for="risk in risks" :key="risk">{{ risk }}</li>
        </ul>
      </div>
      <div v-if="recommendedChecks.length">
        <span class="fusion-list-title">Recommended Checks</span>
        <ul>
          <li v-for="check in recommendedChecks" :key="check">{{ check }}</li>
        </ul>
      </div>
    </div>

    <details class="fusion-raw">
      <summary>Debug details</summary>
      <pre>{{ formattedVerdict }}</pre>
    </details>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  verdict: {
    type: Object,
    required: true
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const data = computed(() => props.verdict?.data || props.verdict || {})
const outcome = computed(() => data.value?.outcome || {})
const title = computed(() => data.value?.title || data.value?.verdict_id || 'Latest fusion verdict')
const status = computed(() => data.value?.status || data.value?.metadata?.status || 'available')
const outcomeLabel = computed(() => {
  if (typeof outcome.value === 'string') return outcome.value
  return outcome.value?.decision
    || outcome.value?.winner
    || outcome.value?.label
    || data.value?.decision
    || data.value?.winner
    || data.value?.label
    || 'Available'
})
const confidence = computed(() => {
  const value = data.value?.confidence ?? outcome.value?.confidence ?? data.value?.probability ?? data.value?.score
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return value <= 1 ? `${Math.round(value * 100)}%` : String(value)
  return String(value)
})
const sourceCount = computed(() => {
  const sources = data.value?.sources || data.value?.evidence || data.value?.source_ids || data.value?.supporting_findings
  return Array.isArray(sources) ? sources.length : '-'
})
const summary = computed(() => data.value?.summary || outcome.value?.summary || '')
const risks = computed(() => {
  const items = data.value?.risks || outcome.value?.risks || []
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const recommendedChecks = computed(() => {
  const items = data.value?.recommended_checks || outcome.value?.recommended_checks || []
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const formattedVerdict = computed(() => JSON.stringify(data.value, null, 2))
</script>

<style scoped>
.fusion-panel {
  border: 1px solid #D8DEE8;
  border-radius: 8px;
  padding: 14px;
  margin: 16px 0 4px;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.fusion-panel.compact {
  margin: 0;
  background: #FFFFFF;
  box-shadow: none;
}

.fusion-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.fusion-kicker,
.fusion-cell span {
  display: block;
  font-size: 10px;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 850;
}

.fusion-header h3 {
  margin: 3px 0 0;
  color: #0F172A;
  font-size: 16px;
  line-height: 1.2;
}

.fusion-status {
  padding: 4px 8px;
  border: 1px solid #A7F3D0;
  border-radius: 999px;
  color: #047857;
  background: #ECFDF5;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.fusion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.fusion-cell {
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  padding: 10px;
  background: #F8FAFC;
}

.fusion-cell strong {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: #111827;
  overflow-wrap: anywhere;
}

.fusion-summary {
  margin: 12px 0 0;
  color: #334155;
  font-size: 12px;
  line-height: 1.5;
}

.fusion-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.fusion-list-title {
  display: block;
  margin-bottom: 6px;
  font-size: 10px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 700;
}

.fusion-lists ul {
  margin: 0;
  padding-left: 18px;
}

.fusion-lists li {
  margin-bottom: 4px;
  color: #374151;
  font-size: 12px;
  line-height: 1.4;
}

.fusion-raw {
  margin-top: 12px;
  font-size: 12px;
}

.fusion-raw summary {
  cursor: pointer;
  color: #475569;
  font-size: 11px;
  font-weight: 800;
}

.fusion-raw pre {
  margin: 8px 0 0;
  padding: 10px;
  border-radius: 6px;
  background: #111827;
  color: #E5E7EB;
  overflow: auto;
  max-height: 260px;
}
</style>
