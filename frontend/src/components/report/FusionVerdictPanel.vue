<template>
  <section class="fusion-panel">
    <div class="fusion-header">
      <div>
        <span class="fusion-kicker">Fusion verdict</span>
        <h3>{{ title }}</h3>
      </div>
      <span class="fusion-status">{{ status }}</span>
    </div>

    <div class="fusion-grid">
      <div class="fusion-cell">
        <span>Decision</span>
        <strong>{{ decision }}</strong>
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

    <details class="fusion-raw">
      <summary>Raw JSON</summary>
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
  }
})

const title = computed(() => props.verdict?.title || props.verdict?.verdict_id || 'Latest fusion verdict')
const status = computed(() => props.verdict?.status || props.verdict?.metadata?.status || 'available')
const decision = computed(() => props.verdict?.decision || props.verdict?.winner || props.verdict?.label || 'See JSON')
const confidence = computed(() => {
  const value = props.verdict?.confidence ?? props.verdict?.probability ?? props.verdict?.score
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return value <= 1 ? `${Math.round(value * 100)}%` : String(value)
  return String(value)
})
const sourceCount = computed(() => {
  const sources = props.verdict?.sources || props.verdict?.evidence || props.verdict?.source_ids
  return Array.isArray(sources) ? sources.length : '-'
})
const formattedVerdict = computed(() => JSON.stringify(props.verdict, null, 2))
</script>

<style scoped>
.fusion-panel {
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  padding: 14px;
  margin: 16px 0 4px;
  background: #F9FAFB;
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
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.fusion-header h3 {
  margin: 3px 0 0;
  color: #111827;
  font-size: 16px;
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
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px;
  background: #FFFFFF;
}

.fusion-cell strong {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: #111827;
  overflow-wrap: anywhere;
}

.fusion-raw {
  margin-top: 12px;
  font-size: 12px;
}

.fusion-raw summary {
  cursor: pointer;
  color: #4B5563;
  font-weight: 600;
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
