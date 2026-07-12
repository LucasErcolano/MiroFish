<template>
  <div class="observability-dock" :class="{ open }">
    <button class="dock-trigger" type="button" @click="open = !open">
      <span class="trigger-title">Observability</span>
      <span class="trigger-count">{{ availableCount }}/6</span>
    </button>

    <aside v-if="open" class="dock-panel" aria-label="Simulation observability">
      <header class="dock-header">
        <div>
          <p class="kicker">Live Artifacts</p>
          <h2>{{ simulationId }}</h2>
        </div>
        <div class="header-actions">
          <button type="button" @click="load">Refresh</button>
          <button type="button" @click="open = false">Close</button>
        </div>
      </header>

      <section class="feature-grid">
        <button
          v-for="feature in features"
          :key="feature.key"
          type="button"
          class="feature-card"
          :class="{ active: feature.available, selected: activeTab === feature.key }"
          @click="activeTab = feature.key"
        >
          <span class="feature-name">{{ feature.label }}</span>
          <strong>{{ feature.value }}</strong>
          <span class="feature-state">{{ feature.available ? 'available' : 'waiting' }}</span>
        </button>
      </section>

      <nav class="dock-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <main class="dock-body">
        <div v-if="loading" class="empty-state">Loading observability artifacts...</div>
        <div v-else-if="error" class="empty-state error">{{ error }}</div>

        <section v-else-if="activeTab === 'overview'" class="overview-stack">
          <div class="summary-row">
            <span>Simulation directory</span>
            <code>{{ manifest?.paths?.simulation_dir || 'not created yet' }}</code>
          </div>
          <div class="summary-row">
            <span>Artifacts detected</span>
            <strong>{{ availableCount }} of 6</strong>
          </div>
          <div class="notes">
            This panel only reads saved artifacts. Opening it does not restart graph build, deep search,
            simulation, or report generation.
          </div>
        </section>

        <section v-else-if="activeTab === 'dedup'" class="metric-stack">
          <div v-if="!dedupSummary" class="empty-state">No deduplication summary yet.</div>
          <template v-else>
            <div class="metric-grid">
              <div>
                <span>Before</span>
                <strong>{{ dedupSummary.before_entities ?? 0 }}</strong>
              </div>
              <div>
                <span>After</span>
                <strong>{{ dedupSummary.after_entities ?? 0 }}</strong>
              </div>
              <div>
                <span>Removed</span>
                <strong>{{ dedupSummary.removed_entities ?? 0 }}</strong>
              </div>
              <div>
                <span>Reduction</span>
                <strong>{{ dedupSummary.reduction_pct ?? 0 }}%</strong>
              </div>
            </div>
            <pre class="json-box">{{ pretty(dedupSummary) }}</pre>
          </template>
        </section>

        <section v-else-if="activeTab === 'wiki'" class="wiki-split">
          <div v-if="wikiPages.length === 0" class="empty-state">No wiki pages compiled yet.</div>
          <template v-else>
            <ul class="page-list">
              <li v-for="page in wikiPages" :key="page.path">
                <button type="button" :class="{ active: selectedWikiPath === page.path }" @click="selectWiki(page.path)">
                  <span>{{ page.title }}</span>
                  <small>{{ page.kind }}</small>
                </button>
              </li>
            </ul>
            <article class="markdown-view" v-html="wikiHtml"></article>
          </template>
        </section>

        <section v-else-if="activeTab === 'telemetry'" class="metric-stack">
          <div v-if="!telemetryData || telemetryData.records_count === 0" class="empty-state">
            No telemetry file found. This run may not have model-call telemetry enabled.
          </div>
          <template v-else>
            <div class="metric-grid">
              <div>
                <span>Calls</span>
                <strong>{{ telemetryData.totals?.calls || 0 }}</strong>
              </div>
              <div>
                <span>Errors</span>
                <strong>{{ telemetryData.totals?.errors || 0 }}</strong>
              </div>
              <div>
                <span>Tokens</span>
                <strong>{{ formatNumber((telemetryData.totals?.tokens_in || 0) + (telemetryData.totals?.tokens_out || 0)) }}</strong>
              </div>
              <div>
                <span>Cost</span>
                <strong>${{ Number(telemetryData.totals?.cost_usd_est || 0).toFixed(4) }}</strong>
              </div>
            </div>
            <table class="artifact-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Calls</th>
                  <th>Errors</th>
                  <th>p95</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in telemetryData.per_model || []" :key="row.model">
                  <td>{{ row.model }}</td>
                  <td>{{ row.calls }}</td>
                  <td>{{ row.errors }}</td>
                  <td>{{ row.latency_p95_ms }}ms</td>
                </tr>
              </tbody>
            </table>
          </template>
        </section>

        <section v-else-if="activeTab === 'deep'" class="text-artifact">
          <div v-if="!deepSearch?.available" class="empty-state">No Deep Search trace saved for this run.</div>
          <pre v-else>{{ deepSearch.content }}</pre>
        </section>

        <section v-else-if="activeTab === 'routing'" class="metric-stack">
          <div v-if="routingRows.length === 0" class="empty-state">
            Routing audit not available. Run with a model map to enable per-agent routing audit.
          </div>
          <table v-else class="artifact-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Role</th>
                <th>Provider</th>
                <th>Model</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in routingRows" :key="`${row.agent_id}-${idx}`">
                <td>{{ row.agent_id }}</td>
                <td>{{ row.role || '-' }}</td>
                <td>{{ row.provider || '-' }}</td>
                <td>{{ row.model || '-' }}</td>
                <td>{{ row.source || 'default' }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-else-if="activeTab === 'fusion'" class="metric-stack">
          <div v-if="verdicts.length === 0" class="empty-state">No Fusion verdicts linked to this simulation.</div>
          <ul v-else class="verdict-list">
            <li v-for="verdict in verdicts" :key="verdict.path">
              <button type="button" @click="selectVerdict(verdict.path)">
                {{ verdict.path }}
              </button>
            </li>
          </ul>
          <pre v-if="fusionVerdict" class="json-box">{{ pretty(fusionVerdict.data || fusionVerdict) }}</pre>
        </section>
      </main>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { marked } from 'marked'
import { useSimulationArtifacts } from '../composables/useSimulationArtifacts'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  },
  autoRefresh: {
    type: Boolean,
    default: true
  }
})

const open = ref(false)
const activeTab = ref('overview')
const selectedWikiPath = ref('')
const selectedWikiPage = ref(null)
const fusionVerdict = ref(null)
let timer = null

const {
  manifest,
  wiki,
  telemetry,
  audit,
  deepSearch,
  deduplication,
  verdicts,
  loading,
  error,
  load,
  loadWikiPage,
  loadFusionVerdict
} = useSimulationArtifacts(() => props.simulationId)

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'wiki', label: 'Wiki' },
  { key: 'telemetry', label: 'Telemetry' },
  { key: 'deep', label: 'Deep Search' },
  { key: 'routing', label: 'Routing' },
  { key: 'fusion', label: 'Fusion' },
  { key: 'dedup', label: 'Dedup' }
]

const wikiPages = computed(() => wiki.value?.pages || [])
const telemetryData = computed(() => telemetry.value)
const routingRows = computed(() => audit.value?.records || [])
const dedupSummary = computed(() => deduplication.value?.summary || null)

const features = computed(() => [
  { key: 'wiki', label: 'Wiki', available: Boolean(manifest.value?.wiki), value: wikiPages.value.length },
  { key: 'telemetry', label: 'Telemetry', available: Boolean(manifest.value?.telemetry), value: telemetryData.value?.records_count || 0 },
  { key: 'deep', label: 'Deep Search', available: Boolean(manifest.value?.deep_search), value: manifest.value?.deep_search ? 'trace' : '-' },
  { key: 'routing', label: 'Routing', available: Boolean(manifest.value?.audit), value: routingRows.value.length },
  { key: 'fusion', label: 'Fusion', available: verdicts.value.length > 0, value: verdicts.value.length },
  { key: 'dedup', label: 'Dedup', available: Boolean(manifest.value?.deduplication), value: dedupSummary.value?.removed_entities ?? '-' }
])

const availableCount = computed(() => features.value.filter(feature => feature.available).length)

const wikiHtml = computed(() => {
  const content = selectedWikiPage.value?.content || ''
  return content ? marked.parse(content) : '<p class="empty-inline">Select a wiki page.</p>'
})

const formatNumber = (value) => Number(value || 0).toLocaleString()
const pretty = (value) => JSON.stringify(value, null, 2)

const selectWiki = async (path) => {
  selectedWikiPath.value = path
  selectedWikiPage.value = await loadWikiPage(path)
}

const selectVerdict = async (path) => {
  fusionVerdict.value = await loadFusionVerdict(path)
}

watch(wikiPages, async (pages) => {
  if (!selectedWikiPath.value && pages.length > 0) {
    await selectWiki(pages[0].path)
  }
})

onMounted(() => {
  load()
  if (props.autoRefresh) {
    timer = window.setInterval(load, 15000)
  }
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.observability-dock {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1200;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.dock-trigger {
  border: 1px solid #111827;
  background: #111827;
  color: #fff;
  height: 42px;
  padding: 0 14px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(17, 24, 39, 0.22);
}

.trigger-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.trigger-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #A7F3D0;
}

.dock-panel {
  position: fixed;
  top: 74px;
  right: 20px;
  bottom: 76px;
  width: min(760px, calc(100vw - 40px));
  background: #fff;
  border: 1px solid #E5E7EB;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dock-header {
  padding: 18px 20px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.kicker {
  margin: 0 0 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6B7280;
}

.dock-header h2 {
  margin: 0;
  font-size: 18px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.header-actions button,
.dock-tabs button,
.feature-card,
.page-list button,
.verdict-list button {
  border: 1px solid #E5E7EB;
  background: #fff;
  color: #111827;
  border-radius: 6px;
  cursor: pointer;
}

.header-actions button {
  height: 32px;
  padding: 0 10px;
  font-size: 12px;
}

.feature-grid {
  padding: 14px 20px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  border-bottom: 1px solid #E5E7EB;
}

.feature-card {
  min-height: 78px;
  padding: 10px;
  text-align: left;
  background: #F9FAFB;
}

.feature-card.active {
  border-color: #111827;
  background: #fff;
}

.feature-card.selected {
  box-shadow: inset 0 0 0 2px #111827;
}

.feature-name,
.feature-state,
.metric-grid span,
.summary-row span {
  display: block;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6B7280;
}

.feature-card strong {
  display: block;
  margin: 8px 0;
  font-size: 18px;
}

.dock-tabs {
  padding: 10px 20px;
  display: flex;
  gap: 6px;
  overflow-x: auto;
  border-bottom: 1px solid #E5E7EB;
}

.dock-tabs button {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
  white-space: nowrap;
}

.dock-tabs button.active {
  background: #111827;
  color: #fff;
  border-color: #111827;
}

.dock-body {
  flex: 1;
  overflow: auto;
  padding: 18px 20px 22px;
}

.empty-state {
  border: 1px dashed #CBD5E1;
  background: #F8FAFC;
  color: #64748B;
  padding: 18px;
  border-radius: 6px;
  font-size: 13px;
}

.empty-state.error {
  border-color: #FCA5A5;
  background: #FEF2F2;
  color: #991B1B;
}

.overview-stack,
.metric-stack,
.text-artifact {
  display: grid;
  gap: 12px;
}

.summary-row {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
  display: grid;
  gap: 6px;
}

.summary-row code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #111827;
  overflow-wrap: anywhere;
}

.notes {
  border-left: 3px solid #111827;
  padding: 10px 12px;
  background: #F9FAFB;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-grid > div {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
}

.metric-grid strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
}

.json-box,
.text-artifact pre {
  margin: 0;
  padding: 14px;
  border-radius: 6px;
  background: #0F172A;
  color: #E2E8F0;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
}

.wiki-split {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 14px;
  min-height: 420px;
}

.page-list,
.verdict-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 6px;
  align-content: start;
}

.page-list button,
.verdict-list button {
  width: 100%;
  padding: 10px;
  text-align: left;
}

.page-list button.active {
  border-color: #111827;
  background: #F3F4F6;
}

.page-list span {
  display: block;
  font-size: 13px;
  font-weight: 700;
}

.page-list small {
  color: #6B7280;
}

.markdown-view {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 16px;
  min-width: 0;
  overflow: auto;
}

.artifact-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.artifact-table th,
.artifact-table td {
  border-bottom: 1px solid #E5E7EB;
  padding: 9px 8px;
  text-align: left;
}

.artifact-table th {
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 10px;
}

@media (max-width: 760px) {
  .dock-panel {
    top: 68px;
    right: 10px;
    bottom: 68px;
    width: calc(100vw - 20px);
  }

  .feature-grid,
  .metric-grid,
  .wiki-split {
    grid-template-columns: 1fr;
  }
}
</style>
