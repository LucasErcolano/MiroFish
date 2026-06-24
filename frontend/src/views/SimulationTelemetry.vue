<template>
  <div class="observability-view">
    <header class="obs-header">
      <button class="brand" @click="router.push('/')">MIROFISH</button>
      <nav class="tabs">
        <router-link :to="{ name: 'Simulation', params: { simulationId } }">Overview</router-link>
        <router-link :to="{ name: 'SimulationWiki', params: { simulationId } }">Wiki</router-link>
        <router-link :to="{ name: 'SimulationTelemetry', params: { simulationId } }">Telemetry</router-link>
      </nav>
    </header>

    <main class="obs-main">
      <section class="page-title">
        <p class="eyebrow">LLM TELEMETRY</p>
        <h1>Model calls, cost and latency</h1>
      </section>

      <div v-if="loading" class="empty">Loading telemetry...</div>
      <div v-else-if="!telemetryData" class="empty">No telemetry recorded for this simulation.</div>
      <template v-else>
        <section class="kpi-grid">
          <div class="kpi">
            <span class="label">Calls</span>
            <strong>{{ totals.calls || 0 }}</strong>
          </div>
          <div class="kpi">
            <span class="label">Errors</span>
            <strong>{{ totals.errors || 0 }}</strong>
          </div>
          <div class="kpi">
            <span class="label">Tokens</span>
            <strong>{{ formatNumber((totals.tokens_in || 0) + (totals.tokens_out || 0)) }}</strong>
          </div>
          <div class="kpi">
            <span class="label">Cost</span>
            <strong>${{ Number(totals.cost_usd_est || 0).toFixed(4) }}</strong>
          </div>
        </section>

        <section class="chart-grid">
          <div class="chart-panel">
            <h2>Cost by model</h2>
            <ModelCostChart :rows="rows" />
          </div>
          <div class="chart-panel">
            <h2>Latency by model</h2>
            <ModelLatencyChart :rows="rows" />
          </div>
        </section>

        <section class="table-panel">
          <h2>Per-model details</h2>
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Provider</th>
                <th>Calls</th>
                <th>Errors</th>
                <th>Tokens in</th>
                <th>Tokens out</th>
                <th>p50</th>
                <th>p95</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.model">
                <td>{{ row.model }}</td>
                <td>{{ row.provider || '-' }}</td>
                <td>{{ row.calls }}</td>
                <td>{{ row.errors }}</td>
                <td>{{ formatNumber(row.tokens_in) }}</td>
                <td>{{ formatNumber(row.tokens_out) }}</td>
                <td>{{ row.latency_p50_ms }}ms</td>
                <td>{{ row.latency_p95_ms }}ms</td>
                <td>${{ Number(row.cost_usd_est || 0).toFixed(4) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSimulationArtifacts } from '../composables/useSimulationArtifacts'

const ModelCostChart = defineAsyncComponent(() => import('../components/charts/ModelCostChart.vue'))
const ModelLatencyChart = defineAsyncComponent(() => import('../components/charts/ModelLatencyChart.vue'))

const props = defineProps({
  simulationId: String
})

const router = useRouter()
const { telemetry, loading, load } = useSimulationArtifacts(() => props.simulationId)

const telemetryData = computed(() => telemetry.value)
const totals = computed(() => telemetry.value?.totals || {})
const rows = computed(() => telemetry.value?.per_model || [])

const formatNumber = (value) => Number(value || 0).toLocaleString()

onMounted(load)
</script>

<style scoped>
.observability-view {
  min-height: 100vh;
  background: #F8FAFC;
  color: #111827;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.obs-header {
  height: 60px;
  padding: 0 24px;
  background: #FFF;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  border: 0;
  background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  cursor: pointer;
}

.tabs {
  display: flex;
  gap: 8px;
}

.tabs a {
  padding: 8px 12px;
  border-radius: 6px;
  color: #6B7280;
  text-decoration: none;
  font-size: 13px;
}

.tabs a.router-link-active {
  background: #111827;
  color: #FFF;
}

.obs-main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px;
}

.page-title .eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: #6B7280;
  letter-spacing: .08em;
}

.page-title h1 {
  margin: 0 0 24px;
  font-size: 28px;
}

.empty,
.kpi,
.chart-panel,
.table-panel {
  background: #FFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}

.empty {
  padding: 36px;
  color: #6B7280;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi {
  padding: 18px;
}

.kpi .label {
  display: block;
  color: #6B7280;
  font-size: 12px;
  margin-bottom: 8px;
}

.kpi strong {
  font-size: 24px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.chart-panel {
  height: 320px;
  padding: 18px;
}

.chart-panel h2,
.table-panel h2 {
  margin: 0 0 16px;
  font-size: 16px;
}

.table-panel {
  padding: 18px;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 10px;
  border-bottom: 1px solid #E5E7EB;
  text-align: left;
}

th {
  color: #6B7280;
  font-size: 11px;
  text-transform: uppercase;
}

@media (max-width: 900px) {
  .kpi-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
