<template>
  <span class="runtime-cost-badge" :class="[`runtime-cost-badge--${statusTone}`, { compact }]">
    <span class="cost-dot" aria-hidden="true"></span>
    <span class="cost-label">{{ label || 'No telemetry' }}</span>
    <small v-if="caption">{{ caption }}</small>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: 'No telemetry'
  },
  status: {
    type: String,
    default: 'none'
  },
  caption: {
    type: String,
    default: ''
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const statusTone = computed(() => {
  if (['unknown', 'partial'].includes(props.status)) return 'warning'
  if (props.status === 'estimated') return 'ready'
  return 'muted'
})
</script>

<style scoped>
.runtime-cost-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 7px 10px;
  border: 1px solid #D8DEE8;
  border-radius: 999px;
  background: #FFFFFF;
  color: #1F2937;
  font-size: 11px;
  font-weight: 750;
  line-height: 1;
  white-space: nowrap;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.runtime-cost-badge.compact {
  min-height: 28px;
  padding: 5px 9px;
  font-size: 10px;
}

.cost-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94A3B8;
  box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.14);
}

.cost-label {
  display: inline-flex;
  align-items: center;
}

.runtime-cost-badge small {
  color: #64748B;
  font-size: 10px;
  font-weight: 650;
}

.runtime-cost-badge--ready {
  border-color: #A7F3D0;
  background: #F0FDF4;
  color: #065F46;
}

.runtime-cost-badge--ready .cost-dot {
  background: #10B981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.14);
}

.runtime-cost-badge--warning {
  border-color: #F6D68B;
  background: #FFFBEB;
  color: #92400E;
}

.runtime-cost-badge--warning .cost-dot {
  background: #F59E0B;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
}

.runtime-cost-badge--muted {
  border-color: #E2E8F0;
  background: #F8FAFC;
  color: #64748B;
}
</style>
