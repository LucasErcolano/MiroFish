<template>
  <div class="wiki-view-shell">
    <header class="wiki-topbar">
      <button class="brand" @click="router.push('/')">MIROFISH</button>
      <nav class="tabs">
        <router-link :to="{ name: 'Simulation', params: { simulationId } }">Overview</router-link>
        <router-link :to="{ name: 'SimulationWiki', params: { simulationId } }">Wiki</router-link>
        <router-link :to="{ name: 'SimulationTelemetry', params: { simulationId } }">Debug telemetry</router-link>
      </nav>
    </header>

    <main class="wiki-workspace">
      <aside class="wiki-sidebar">
        <div class="wiki-sidebar-heading">
          <span>Evidence Wiki</span>
          <strong>{{ pages.length }} pages</strong>
        </div>
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
              <span>{{ page.displayTitle }}</span>
              <small>{{ page.displayKind }}</small>
            </button>
          </section>
        </template>
      </aside>

      <section class="wiki-reader">
        <div v-if="pageLoading" class="empty">Loading page...</div>
        <div v-else-if="!selectedPath" class="empty">Select a wiki page to inspect.</div>
        <template v-else>
          <div class="wiki-reader-header">
            <span>{{ selectedPage?.displayKind || 'Wiki Page' }}</span>
            <h1>{{ selectedPage?.displayTitle || 'Wiki Page' }}</h1>
            <p>Readable context compiled from the simulation evidence layer.</p>
          </div>
          <article class="markdown-body" v-html="renderedContent"></article>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import { useSimulationArtifacts } from '../composables/useSimulationArtifacts'
import { normalizeWikiPages } from '../composables/useObservabilitySummary'

marked.setOptions({ gfm: true, breaks: false })

const props = defineProps({
  simulationId: String
})

const router = useRouter()
const { wiki, loading, load, loadWikiPage } = useSimulationArtifacts(() => props.simulationId)
const selectedPath = ref('')
const pageContent = ref('')
const pageLoading = ref(false)

const pages = computed(() => normalizeWikiPages(wiki.value?.pages || []))
const selectedPage = computed(() => pages.value.find(page => page.path === selectedPath.value) || null)
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
  return marked.parse(cleanWikiContent(pageContent.value))
})

const cleanWikiContent = (content) => {
  return String(content || '')
    .replace(/^#\s*Simulation\s+sim_[\w-]+\s+(?:\u2014|-)\s+Wiki\s+Index/m, '# Wiki Index')
    .replace(/^#\s*Simulation\s+sim_[\w-]+\s+(?:\u2014|-)\s+/m, '# ')
    .replace(/Simulation\s+\*\*sim_[^*]+\*\*\s+(?:\u2014|-)\s+/g, '')
    .replace(/Simulation\s+sim_[\w-]+\s+(?:\u2014|-)\s+/g, '')
    .replace(/Simulation\s+sim_[\w-]+\s+agent knowledge base/g, 'Agent knowledge base')
    .replace(/\bsim_[\w-]+\b/g, 'this simulation')
}

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

onMounted(async () => {
  await load()
  const first = pages.value.find(page => page.path === 'index.md') || pages.value[0]
  if (first) await selectPage(first.path)
})

watch(() => props.simulationId, async () => {
  selectedPath.value = ''
  pageContent.value = ''
  await load()
  const first = pages.value.find(page => page.path === 'index.md') || pages.value[0]
  if (first) await selectPage(first.path)
})
</script>

<style scoped>
.wiki-view-shell {
  height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(226, 232, 240, 0.65), transparent 32%),
    #F8FAFC;
  color: #0F172A;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}

.wiki-topbar {
  height: 60px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  backdrop-filter: blur(12px);
}

.brand {
  border: 0;
  background: transparent;
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 850;
  cursor: pointer;
  letter-spacing: 0.02em;
}

.tabs {
  display: flex;
  gap: 8px;
}

.tabs a {
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #64748B;
  text-decoration: none;
  font-size: 12px;
  font-weight: 750;
}

.tabs a.router-link-active {
  background: #0F172A;
  border-color: #0F172A;
  color: #FFFFFF;
}

.wiki-workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
}

.wiki-sidebar {
  background: rgba(255, 255, 255, 0.96);
  border-right: 1px solid #E2E8F0;
  padding: 20px;
  overflow-y: auto;
}

.wiki-sidebar-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}

.wiki-sidebar-heading span {
  color: #0F172A;
  font-size: 18px;
  font-weight: 850;
  line-height: 1.1;
}

.wiki-sidebar-heading strong {
  flex-shrink: 0;
  padding: 5px 8px;
  border: 1px solid #E2E8F0;
  border-radius: 999px;
  background: #F8FAFC;
  color: #334155;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.tree-empty {
  color: #64748B;
  font-size: 13px;
}

.tree-group {
  margin-bottom: 20px;
}

.tree-group h2 {
  margin: 0 0 8px;
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tree-item {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 8px;
  padding: 9px 10px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
}

.tree-item:hover {
  background: #F8FAFC;
  border-color: #E2E8F0;
}

.tree-item.active {
  background: #EEF2FF;
  border-color: #CBD5E1;
}

.tree-item span {
  min-width: 0;
  color: #0F172A;
  font-size: 12px;
  font-weight: 750;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-item small {
  color: #64748B;
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
}

.wiki-reader {
  min-width: 0;
  overflow-y: auto;
  padding: 28px;
}

.wiki-reader-header,
.empty,
.markdown-body {
  max-width: 920px;
  margin: 0 auto;
}

.wiki-reader-header {
  padding: 24px 28px;
  border: 1px solid #D8DEE8;
  border-radius: 10px 10px 0 0;
  background: #FFFFFF;
  border-bottom: 0;
}

.wiki-reader-header span {
  display: block;
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.wiki-reader-header h1 {
  margin: 5px 0 0;
  color: #0F172A;
  font-size: 30px;
  font-weight: 850;
  line-height: 1.08;
}

.wiki-reader-header p {
  margin: 8px 0 0;
  color: #64748B;
  font-size: 13px;
  font-weight: 650;
}

.empty,
.markdown-body {
  background: #FFFFFF;
  border: 1px solid #D8DEE8;
  border-radius: 10px;
  padding: 28px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.wiki-reader-header + .markdown-body {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.empty {
  color: #64748B;
}

.markdown-body {
  color: #1E293B;
  font-size: 15px;
  line-height: 1.68;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 1.2em 0 0.45em;
  color: #0F172A;
  line-height: 1.18;
}

.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p) {
  margin: 0.65em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 0.35em 0;
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: #F1F5F9;
  color: #0F172A;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88em;
}

.markdown-body :deep(pre) {
  white-space: pre-wrap;
  background: #0F172A;
  color: #E2E8F0;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

@media (max-width: 900px) {
  .wiki-topbar {
    align-items: flex-start;
    height: auto;
    padding: 14px 16px;
    flex-direction: column;
    gap: 12px;
  }

  .tabs {
    width: 100%;
    overflow-x: auto;
  }

  .wiki-workspace {
    grid-template-columns: 1fr;
  }

  .wiki-sidebar {
    max-height: 320px;
    border-right: 0;
    border-bottom: 1px solid #E2E8F0;
  }

  .wiki-reader {
    padding: 18px;
  }

  .wiki-reader-header h1 {
    font-size: 24px;
  }
}
</style>
