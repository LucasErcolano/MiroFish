<template>
  <div class="evidence-metric-strip" :class="{ dense }">
    <div
      v-for="metric in visibleMetrics"
      :key="metric.key || metric.label"
      class="evidence-metric"
      :class="`evidence-metric--${metric.tone || 'neutral'}`"
    >
      <span class="metric-label">{{ metric.label }}</span>
      <strong class="metric-value">{{ metric.value }}</strong>
      <small v-if="metric.hint">{{ metric.hint }}</small>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  metrics: {
    type: Array,
    default: () => []
  },
  dense: {
    type: Boolean,
    default: false
  }
})

const visibleMetrics = computed(() => props.metrics.filter(Boolean))
</script>

<style scoped>
.evidence-metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
  gap: 8px;
}

.evidence-metric-strip.dense {
  grid-template-columns: repeat(auto-fit, minmax(88px, 1fr));
  gap: 7px;
}

.evidence-metric {
  min-width: 0;
  padding: 10px 11px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.evidence-metric-strip.dense .evidence-metric {
  padding: 8px 9px;
}

.metric-label {
  display: block;
  margin-bottom: 4px;
  color: #64748B;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.06em;
  line-height: 1.2;
  text-transform: uppercase;
}

.metric-value {
  display: block;
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.evidence-metric-strip.dense .metric-value {
  font-size: 12px;
}

.evidence-metric small {
  display: block;
  margin-top: 3px;
  color: #94A3B8;
  font-size: 10px;
  font-weight: 650;
  line-height: 1.25;
}

.evidence-metric--ready {
  border-color: #BBF7D0;
  background: linear-gradient(180deg, #FFFFFF 0%, #F0FDF4 100%);
}

.evidence-metric--warning {
  border-color: #FDE68A;
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFBEB 100%);
}

.evidence-metric--active {
  border-color: #CBD5E1;
  background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%);
}
</style>
