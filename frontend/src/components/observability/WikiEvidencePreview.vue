<template>
  <section class="wiki-evidence-preview">
    <div class="wiki-preview-header">
      <div>
        <span class="wiki-kicker">{{ t('observability.wikiPreview.kicker') }}</span>
        <h4>{{ t('observability.wikiPreview.pagesCompiled', { count: totalPages }) }}</h4>
      </div>
      <button type="button" class="wiki-open-action" @click="$emit('open')">
        {{ t('observability.openWiki') }}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 17L17 7"></path>
          <path d="M9 7h8v8"></path>
        </svg>
      </button>
    </div>

    <div class="wiki-map">
      <div
        v-for="row in mapRows"
        :key="row.key"
        class="wiki-map-row"
        :class="{ ready: row.ready }"
      >
        <span class="wiki-map-name">{{ row.label }}</span>
        <strong>{{ row.value }}</strong>
        <small>{{ row.hint }}</small>
      </div>
    </div>

    <div v-if="previewPages.length" class="wiki-page-preview">
      <span class="wiki-preview-label">{{ t('observability.wikiPreview.latestPages') }}</span>
      <div v-for="page in previewPages" :key="page.path" class="wiki-page-row">
        <span>{{ page.displayTitle || page.title }}</span>
        <small>{{ page.displayKind || page.kind }}</small>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  pages: {
    type: Array,
    default: () => []
  },
  stats: {
    type: Object,
    default: null
  },
  maxRows: {
    type: Number,
    default: 5
  }
})

defineEmits(['open'])

const totalPages = computed(() => props.stats?.total || props.pages.length || 0)
const entityCount = computed(() => props.stats?.entities || props.pages.filter(page => page.kind === 'entity').length)
const claimCount = computed(() => props.stats?.claims || props.pages.filter(page => page.kind === 'claim').length)

const findPage = (label) => {
  const wanted = label.toLowerCase()
  return props.pages.find(page => String(page.displayTitle || page.title || '').toLowerCase() === wanted)
    || props.pages.find(page => String(page.displayTitle || page.title || '').toLowerCase().includes(wanted))
}

const pageState = (label, fallbackHint) => {
  const page = findPage(label)
  return {
    ready: Boolean(page),
    value: page ? 'Ready' : 'Pending',
    hint: page?.displayKind || fallbackHint
  }
}

const mapRows = computed(() => {
  const overview = pageState('Overview', 'Root page')
  const agents = pageState('Agents', 'Agent profiles')
  const timeline = pageState('Timeline', 'Simulation chronology')

  return [
    { key: 'overview', label: 'Overview', ...overview },
    { key: 'agents', label: 'Agents', ...agents },
    { key: 'timeline', label: 'Timeline', ...timeline },
    {
      key: 'claims',
      label: 'Claims',
      ready: claimCount.value > 0,
      value: claimCount.value ? `${claimCount.value}` : '0',
      hint: 'Claim pages'
    },
    {
      key: 'entities',
      label: 'Entities',
      ready: entityCount.value > 0,
      value: entityCount.value ? `${entityCount.value}` : '0',
      hint: 'Entity pages'
    }
  ]
})

const previewPages = computed(() => props.pages.slice(0, props.maxRows))
</script>

<style scoped>
.wiki-evidence-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wiki-preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.wiki-kicker,
.wiki-preview-label {
  display: block;
  color: #64748B;
  font-size: 9px;
  font-weight: 850;
  letter-spacing: 0.06em;
  line-height: 1.2;
  text-transform: uppercase;
}

.wiki-preview-header h4 {
  margin: 3px 0 0;
  color: #0F172A;
  font-size: 14px;
  line-height: 1.2;
}

.wiki-open-action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 6px 9px;
  border: 1px solid #0F172A;
  border-radius: 6px;
  background: #0F172A;
  color: #FFFFFF;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.wiki-open-action:hover {
  background: #1E293B;
  border-color: #1E293B;
}

.wiki-open-action svg {
  width: 13px;
  height: 13px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.wiki-map {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(82px, 1fr));
  gap: 7px;
}

.wiki-map-row {
  min-width: 0;
  padding: 8px;
  border: 1px dashed #CBD5E1;
  border-radius: 8px;
  background: #F8FAFC;
}

.wiki-map-row.ready {
  border-style: solid;
  border-color: #BBF7D0;
  background: #F0FDF4;
}

.wiki-map-name {
  display: block;
  color: #334155;
  font-size: 11px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wiki-map-row strong {
  display: block;
  margin-top: 4px;
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.wiki-map-row small {
  display: block;
  margin-top: 2px;
  color: #64748B;
  font-size: 10px;
  line-height: 1.2;
}

.wiki-page-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.wiki-page-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-width: 0;
  padding: 7px 8px;
  border: 1px solid #E2E8F0;
  border-radius: 7px;
  background: #FFFFFF;
}

.wiki-page-row span {
  min-width: 0;
  color: #0F172A;
  font-size: 12px;
  font-weight: 750;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wiki-page-row small {
  color: #64748B;
  font-size: 10px;
  font-weight: 700;
}
</style>
