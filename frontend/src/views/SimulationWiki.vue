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

    <main class="wiki-layout">
      <aside class="wiki-tree">
        <div class="tree-title">Report Wiki</div>
        <div v-if="loading" class="tree-empty">Loading...</div>
        <div v-else-if="pages.length === 0" class="tree-empty">No wiki available for this simulation.</div>
        <template v-else>
          <section v-for="group in groupedPages" :key="group.kind" class="tree-group">
            <h2>{{ group.label }}</h2>
            <button
              v-for="page in group.pages"
              :key="page.path"
              class="tree-item"
              :class="{ active: selectedPath === page.path }"
              @click="selectPage(page.path)"
            >
              <span>{{ page.title }}</span>
              <small>{{ formatBytes(page.size) }}</small>
            </button>
          </section>
        </template>
      </aside>

      <section class="wiki-content">
        <div v-if="pageLoading" class="empty">Loading page...</div>
        <div v-else-if="!selectedPath" class="empty">Select a wiki page to inspect.</div>
        <article v-else class="markdown-body" v-html="renderedContent"></article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import { useSimulationArtifacts } from '../composables/useSimulationArtifacts'

marked.setOptions({ gfm: true, breaks: false })

const props = defineProps({
  simulationId: String
})

const router = useRouter()
const { wiki, loading, load, loadWikiPage } = useSimulationArtifacts(() => props.simulationId)
const selectedPath = ref('')
const pageContent = ref('')
const pageLoading = ref(false)

const pages = computed(() => wiki.value?.pages || [])
const groupedPages = computed(() => {
  const labels = {
    root: 'Overview pages',
    entity: 'Entities',
    claim: 'Claims',
    meta: 'Metadata'
  }
  return ['root', 'entity', 'claim', 'meta']
    .map(kind => ({ kind, label: labels[kind], pages: pages.value.filter(page => page.kind === kind) }))
    .filter(group => group.pages.length > 0)
})

const renderedContent = computed(() => {
  if (!pageContent.value) return ''
  if (selectedPath.value.endsWith('.json')) {
    try {
      return `<pre>${JSON.stringify(JSON.parse(pageContent.value), null, 2)}</pre>`
    } catch {
      return `<pre>${pageContent.value}</pre>`
    }
  }
  return marked.parse(pageContent.value)
})

const selectPage = async (path) => {
  selectedPath.value = path
  pageLoading.value = true
  try {
    const res = await loadWikiPage(path)
    pageContent.value = res.content || ''
  } finally {
    pageLoading.value = false
  }
}

const formatBytes = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
}

onMounted(async () => {
  await load()
  const first = pages.value.find(page => page.path === 'index.md') || pages.value[0]
  if (first) await selectPage(first.path)
})

watch(() => props.simulationId, async () => {
  selectedPath.value = ''
  pageContent.value = ''
  await load()
})
</script>

<style scoped>
.observability-view {
  height: 100vh;
  background: #F8FAFC;
  color: #111827;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}

.obs-header {
  height: 60px;
  padding: 0 24px;
  background: #FFF;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
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

.wiki-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 320px 1fr;
}

.wiki-tree {
  background: #FFF;
  border-right: 1px solid #E5E7EB;
  padding: 20px;
  overflow-y: auto;
}

.tree-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 18px;
}

.tree-empty {
  color: #6B7280;
  font-size: 13px;
}

.tree-group {
  margin-bottom: 18px;
}

.tree-group h2 {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: #6B7280;
}

.tree-item {
  width: 100%;
  border: 0;
  background: transparent;
  border-radius: 6px;
  padding: 9px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  text-align: left;
  cursor: pointer;
}

.tree-item:hover,
.tree-item.active {
  background: #F3F4F6;
}

.tree-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-item small {
  color: #9CA3AF;
  flex-shrink: 0;
}

.wiki-content {
  overflow-y: auto;
  padding: 28px;
}

.empty,
.markdown-body {
  max-width: 920px;
  background: #FFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 28px;
}

.empty {
  color: #6B7280;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 0;
}

.markdown-body :deep(pre) {
  white-space: pre-wrap;
  background: #111827;
  color: #E5E7EB;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
}

@media (max-width: 900px) {
  .wiki-layout {
    grid-template-columns: 1fr;
  }

  .wiki-tree {
    max-height: 320px;
    border-right: 0;
    border-bottom: 1px solid #E5E7EB;
  }
}
</style>
