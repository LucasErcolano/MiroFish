<template>
  <Teleport to="body">
    <Transition name="telemetry-shell" appear @after-leave="emit('close')">
      <div v-if="isVisible" class="telemetry-overlay" @click.self="requestClose">
        <section class="telemetry-drawer" role="dialog" aria-modal="true" :aria-label="t('observability.telemetry.drawerLabel')">
          <header class="telemetry-drawer-header">
            <div>
              <span class="drawer-kicker">{{ t('observability.telemetry.kicker') }}</span>
              <h2>{{ t('observability.telemetry.title') }}</h2>
              <p>{{ t('observability.telemetry.subtitle') }}</p>
            </div>
            <button type="button" class="close-btn" :aria-label="t('common.close')" @click="requestClose">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </header>

          <main class="telemetry-body">
            <div v-if="loading" class="telemetry-empty">{{ t('observability.telemetry.loading') }}</div>
            <div v-else-if="!summary.hasData" class="telemetry-empty">{{ t('observability.telemetry.empty') }}</div>
            <template v-else>
              <section class="telemetry-kpis">
                <div class="telemetry-kpi">
                  <span>{{ t('observability.telemetry.calls') }}</span>
                  <strong>{{ summary.calls }}</strong>
                </div>
                <div class="telemetry-kpi">
                  <span>{{ t('observability.telemetry.errors') }}</span>
                  <strong>{{ summary.errors }}</strong>
                </div>
                <div class="telemetry-kpi">
                  <span>{{ t('observability.telemetry.tokens') }}</span>
                  <strong>{{ formatNumber(summary.tokens) }}</strong>
                </div>
                <div class="telemetry-kpi">
                  <span>{{ t('observability.telemetry.cost') }}</span>
                  <strong>{{ summary.costLabel }}</strong>
                </div>
              </section>

              <section v-if="summary.notices.length" class="telemetry-notices">
                <span v-for="notice in summary.notices" :key="notice">{{ notice }}</span>
              </section>

              <section class="telemetry-charts">
                <div class="chart-panel">
                  <h3>{{ t('observability.telemetry.costByModel') }}</h3>
                  <ModelCostChart :rows="rows" />
                </div>
                <div class="chart-panel">
                  <h3>{{ t('observability.telemetry.latencyByModel') }}</h3>
                  <ModelLatencyChart :rows="rows" />
                </div>
              </section>

              <section class="telemetry-table-panel">
                <div class="table-heading">
                  <h3>{{ t('observability.telemetry.perModel') }}</h3>
                  <span>{{ rows.length }} {{ t('observability.telemetry.models') }}</span>
                </div>
                <div class="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>{{ t('observability.telemetry.model') }}</th>
                        <th>{{ t('observability.telemetry.provider') }}</th>
                        <th>{{ t('observability.telemetry.calls') }}</th>
                        <th>{{ t('observability.telemetry.errors') }}</th>
                        <th>{{ t('observability.telemetry.tokensIn') }}</th>
                        <th>{{ t('observability.telemetry.tokensOut') }}</th>
                        <th>p50</th>
                        <th>p95</th>
                        <th>{{ t('observability.telemetry.cost') }}</th>
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
                        <td>{{ formatCostWithStatus(row.cost_usd_est, row.cost_estimation_status) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </template>
          </main>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSimulationArtifacts } from '../../composables/useSimulationArtifacts'
import {
  formatCostWithStatus,
  formatNumber,
  summarizeTelemetry
} from '../../composables/useObservabilitySummary'

const ModelCostChart = defineAsyncComponent(() => import('../charts/ModelCostChart.vue'))
const ModelLatencyChart = defineAsyncComponent(() => import('../charts/ModelLatencyChart.vue'))

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close'])
const { t } = useI18n()
const { telemetry, loading, load } = useSimulationArtifacts(() => props.simulationId)

const isVisible = ref(false)
const rows = computed(() => telemetry.value?.per_model || [])
const summary = computed(() => summarizeTelemetry(telemetry.value))

const requestClose = () => {
  isVisible.value = false
}

const handleKeydown = (event) => {
  if (event.key === 'Escape') requestClose()
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  requestAnimationFrame(() => {
    isVisible.value = true
  })
  load()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.simulationId, () => {
  load()
})
</script>

<style scoped>
.telemetry-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(6px);
}

.telemetry-drawer {
  width: min(980px, calc(100vw - 28px));
  height: 100vh;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(255, 255, 255, 0.98)),
    #FFFFFF;
  color: #0F172A;
  box-shadow: -24px 0 60px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.telemetry-shell-enter-active,
.telemetry-shell-leave-active {
  transition: opacity 180ms ease;
}

.telemetry-shell-enter-from,
.telemetry-shell-leave-to {
  opacity: 0;
}

.telemetry-shell-enter-active .telemetry-drawer,
.telemetry-shell-leave-active .telemetry-drawer {
  transition:
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease;
}

.telemetry-shell-enter-from .telemetry-drawer {
  opacity: 0.82;
  transform: translateX(42px);
}

.telemetry-shell-leave-to .telemetry-drawer {
  opacity: 0.74;
  transform: translateX(54px);
}

.telemetry-drawer-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 24px 26px 18px;
  border-bottom: 1px solid #E2E8F0;
  background: rgba(255, 255, 255, 0.78);
}

.drawer-kicker {
  display: block;
  margin-bottom: 6px;
  color: #64748B;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.telemetry-drawer-header h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.12;
  color: #0F172A;
}

.telemetry-drawer-header p {
  margin: 7px 0 0;
  color: #64748B;
  font-size: 13px;
  font-weight: 650;
}

.close-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #CBD5E1;
  border-radius: 8px;
  background: #FFFFFF;
  color: #334155;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.close-btn:hover {
  background: #F8FAFC;
  color: #0F172A;
}

.telemetry-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px 24px 28px;
}

.telemetry-empty,
.telemetry-kpi,
.chart-panel,
.telemetry-table-panel {
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.telemetry-empty {
  padding: 34px;
  color: #64748B;
  font-size: 13px;
  font-weight: 650;
}

.telemetry-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.telemetry-kpi {
  padding: 16px;
}

.telemetry-kpi span {
  display: block;
  margin-bottom: 8px;
  color: #64748B;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.telemetry-kpi strong {
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-size: 21px;
  line-height: 1.1;
}

.telemetry-notices {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.telemetry-notices span {
  padding: 5px 9px;
  border: 1px solid #FED7AA;
  border-radius: 999px;
  background: #FFF7ED;
  color: #9A3412;
  font-size: 11px;
  font-weight: 750;
}

.telemetry-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.chart-panel {
  height: 320px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-panel h3,
.table-heading h3 {
  margin: 0 0 12px;
  color: #0F172A;
  font-size: 14px;
  font-weight: 850;
  flex: 0 0 auto;
}

.chart-panel :deep(.model-chart) {
  flex: 1 1 auto;
  min-height: 0;
}

.telemetry-table-panel {
  padding: 16px;
}

.table-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.table-heading span {
  color: #64748B;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 750;
}

.table-scroll {
  overflow: auto;
}

table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 12px;
}

th,
td {
  padding: 9px 8px;
  border-bottom: 1px solid #E2E8F0;
  text-align: left;
  vertical-align: top;
}

th {
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

td {
  color: #334155;
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 760px) {
  .telemetry-drawer {
    width: 100vw;
  }

  .telemetry-drawer-header {
    padding: 20px 18px 16px;
  }

  .telemetry-body {
    padding: 16px;
  }

  .telemetry-kpis,
  .telemetry-charts {
    grid-template-columns: 1fr;
  }

  .chart-panel {
    height: 280px;
  }
}
</style>
