<template>
  <div class="evidence-stage-rail" :class="{ compact }">
    <article
      v-for="(stage, index) in stages"
      :key="stage.key || stage.label"
      class="stage-row"
      :class="`stage-row--${stage.status || 'todo'}`"
    >
      <div class="stage-spine" aria-hidden="true">
        <span class="stage-dot">
          <svg v-if="stage.status === 'done'" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <svg v-else-if="stage.status === 'warning'" viewBox="0 0 24 24">
            <path d="M12 8v5"></path>
            <path d="M12 17h.01"></path>
          </svg>
          <svg v-else-if="stage.status === 'active'" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        </span>
        <span v-if="index < stages.length - 1" class="stage-line"></span>
      </div>

      <details class="stage-card" :open="stage.defaultOpen">
        <summary>
          <span class="stage-copy">
            <span class="stage-label">{{ stage.label }}</span>
            <span v-if="stage.detail" class="stage-detail">{{ stage.detail }}</span>
          </span>
          <span class="stage-value">{{ stage.value }}</span>
        </summary>

        <div class="stage-body">
          <p v-if="stage.summary">{{ stage.summary }}</p>

          <div v-if="stage.meta?.length" class="stage-meta-grid">
            <span v-for="meta in stage.meta" :key="meta.label">
              <small>{{ meta.label }}</small>
              <strong>{{ meta.value }}</strong>
            </span>
          </div>

          <div v-if="stage.notices?.length" class="stage-notices">
            <span v-for="notice in stage.notices" :key="notice">{{ notice }}</span>
          </div>

          <slot :name="stage.key" :stage="stage"></slot>
        </div>
      </details>
    </article>
  </div>
</template>

<script setup>
defineProps({
  stages: {
    type: Array,
    default: () => []
  },
  compact: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.evidence-stage-rail {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.stage-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
}

.stage-spine {
  position: relative;
  display: flex;
  justify-content: center;
}

.stage-dot {
  position: relative;
  z-index: 1;
  width: 22px;
  height: 22px;
  border: 1px solid #CBD5E1;
  border-radius: 50%;
  background: #FFFFFF;
  color: #64748B;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 11px;
  box-shadow: 0 0 0 4px #FFFFFF;
}

.stage-dot svg {
  width: 13px;
  height: 13px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.5;
}

.stage-line {
  position: absolute;
  top: 34px;
  bottom: -10px;
  width: 1px;
  background: #E2E8F0;
}

.stage-card {
  min-width: 0;
  margin-bottom: 10px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.stage-card summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 10px 12px;
  cursor: pointer;
  list-style: none;
}

.stage-card summary::-webkit-details-marker {
  display: none;
}

.stage-card summary::after {
  content: '';
  width: 7px;
  height: 7px;
  border-right: 1.5px solid #64748B;
  border-bottom: 1.5px solid #64748B;
  transform: rotate(45deg);
  transition: transform 0.18s ease;
  justify-self: end;
  grid-column: 2;
  grid-row: 1;
  margin-right: 2px;
}

.stage-card[open] summary::after {
  transform: rotate(225deg);
}

.stage-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.stage-label {
  color: #0F172A;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
}

.stage-detail {
  color: #64748B;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-value {
  min-width: 58px;
  padding-right: 18px;
  color: #334155;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 800;
  text-align: right;
  white-space: nowrap;
}

.stage-body {
  padding: 0 12px 12px;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.stage-body p {
  margin: 0 0 10px;
}

.stage-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(82px, 1fr));
  gap: 7px;
  margin-bottom: 10px;
}

.stage-meta-grid span {
  min-width: 0;
  padding: 8px;
  border: 1px solid #E2E8F0;
  border-radius: 7px;
  background: #F8FAFC;
}

.stage-meta-grid small {
  display: block;
  margin-bottom: 3px;
  color: #94A3B8;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.stage-meta-grid strong {
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  overflow-wrap: anywhere;
}

.stage-notices {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.stage-notices span {
  padding: 4px 8px;
  border: 1px solid #FED7AA;
  border-radius: 999px;
  background: #FFF7ED;
  color: #9A3412;
  font-size: 10px;
  font-weight: 750;
}

.stage-row--done .stage-dot {
  border-color: #86EFAC;
  background: #ECFDF5;
  color: #059669;
}

.stage-row--active .stage-dot {
  border-color: #0F172A;
  background: #0F172A;
  color: #FFFFFF;
}

.stage-row--warning .stage-dot {
  border-color: #FCD34D;
  background: #FFFBEB;
  color: #B45309;
}

.stage-row--todo .stage-card {
  background: #F8FAFC;
}

.stage-row--todo .stage-label,
.stage-row--todo .stage-value {
  color: #64748B;
}

.evidence-stage-rail.compact .stage-row {
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 8px;
}

.evidence-stage-rail.compact .stage-dot {
  width: 18px;
  height: 18px;
  margin-top: 10px;
}

.evidence-stage-rail.compact .stage-dot svg {
  width: 11px;
  height: 11px;
}

.evidence-stage-rail.compact .stage-card summary {
  min-height: 40px;
  padding: 8px 10px;
}

.evidence-stage-rail.compact .stage-body {
  padding: 0 10px 10px;
}
</style>
