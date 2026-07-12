<template>
  <Teleport to="body">
    <Transition name="wiki-shell" appear @after-leave="emit('close')">
      <div v-if="isVisible" class="wiki-overlay" @click.self="requestClose">
        <section class="wiki-drawer" role="dialog" aria-modal="true" :aria-label="t('observability.wikiDrawer.drawerLabel')">
          <header class="wiki-drawer-header">
            <div>
              <span class="drawer-kicker">{{ t('observability.wikiDrawer.kicker') }}</span>
              <h2>{{ t('observability.wikiDrawer.title') }}</h2>
              <p>{{ t('observability.wikiDrawer.subtitle') }}</p>
            </div>
            <button type="button" class="close-btn" :aria-label="t('common.close')" @click="requestClose">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </header>

          <div class="quick-pages" v-if="quickPages.length">
            <button
              v-for="item in quickPages"
              :key="item.key"
              type="button"
              class="quick-page"
              :class="{ active: selectedPath === item.path, disabled: !item.path }"
              :disabled="!item.path"
              @click="selectPage(item.path)"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.count }}</strong>
            </button>
          </div>

          <main class="wiki-drawer-body">
            <aside class="wiki-nav">
              <div class="nav-heading">
                <span>{{ t('observability.wikiDrawer.pages') }}</span>
                <strong>{{ pages.length }}</strong>
              </div>

              <div v-if="loading" class="wiki-empty">{{ t('observability.wikiDrawer.loading') }}</div>
              <div v-else-if="pages.length === 0" class="wiki-empty">{{ t('observability.wikiDrawer.empty') }}</div>
              <template v-else>
                <section v-for="group in groupedPages" :key="group.kind" class="tree-group">
                  <h3>{{ group.label }}</h3>
                  <button
                    v-for="page in group.pages"
                    :key="page.path"
                    type="button"
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
              <Transition name="wiki-page" mode="out-in">
                <div v-if="pageLoading" key="loading" class="reader-empty">{{ t('observability.wikiDrawer.loadingPage') }}</div>
                <div v-else-if="!selectedPath" key="empty" class="reader-empty">{{ t('observability.wikiDrawer.selectPage') }}</div>
                <div v-else :key="selectedPath" class="reader-article-frame">
                  <div class="reader-header">
                    <span>{{ selectedPage?.displayKind || 'Wiki Page' }}</span>
                    <h1>{{ selectedPage?.displayTitle || 'Wiki Page' }}</h1>
                    <p>{{ t('observability.wikiDrawer.readerSubtitle') }}</p>
                  </div>
                  <article class="markdown-body" v-html="renderedContent"></article>
                </div>
              </Transition>
            </section>
          </main>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { marked } from 'marked'
import { useSimulationArtifacts } from '../../composables/useSimulationArtifacts'
import { normalizeWikiPages } from '../../composables/useObservabilitySummary'

marked.setOptions({ gfm: true, breaks: false })

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close'])
const { t } = useI18n()

const { wiki, loading, load, loadWikiPage } = useSimulationArtifacts(() => props.simulationId)
const isVisible = ref(false)
const selectedPath = ref('')
const pageContent = ref('')
const pageLoading = ref(false)

const pages = computed(() => normalizeWikiPages(wiki.value?.pages || []))
const selectedPage = computed(() => pages.value.find(page => page.path === selectedPath.value) || null)
const groupedPages = computed(() => {
  const labels = {
    root: 'Overview',
    entity: 'Entities',
    claim: 'Claims',
    meta: 'Metadata'
  }
  return ['root', 'entity', 'claim', 'meta']
    .map(kind => ({ kind, label: labels[kind], pages: pages.value.filter(page => page.kind === kind) }))
    .filter(group => group.pages.length > 0)
})

const quickPages = computed(() => {
  const findPage = (paths, kind) => pages.value.find(page => paths.includes(page.path))
    || pages.value.find(page => page.kind === kind)

  const overview = findPage(['index.md', 'overview.md'], 'root')
  const agents = findPage(['agents.md'], 'root')
  const timeline = findPage(['timeline.md'], 'root')
  const claims = pages.value.find(page => page.kind === 'claim')
  const entities = pages.value.find(page => page.kind === 'entity')

  return [
    { key: 'overview', label: 'Overview', path: overview?.path, count: overview ? 'Open' : '-' },
    { key: 'agents', label: 'Agents', path: agents?.path, count: agents ? 'Open' : '-' },
    { key: 'timeline', label: 'Timeline', path: timeline?.path, count: timeline ? 'Open' : '-' },
    { key: 'claims', label: 'Claims', path: claims?.path, count: pages.value.filter(page => page.kind === 'claim').length || '-' },
    { key: 'entities', label: 'Entities', path: entities?.path, count: pages.value.filter(page => page.kind === 'entity').length || '-' }
  ]
})

const renderedContent = computed(() => {
  if (!pageContent.value) return ''
  if (selectedPath.value.endsWith('.json')) {
    try {
      return `<pre>${escapeHtml(JSON.stringify(JSON.parse(pageContent.value), null, 2))}</pre>`
    } catch {
      return `<pre>${escapeHtml(pageContent.value)}</pre>`
    }
  }
  return marked.parse(cleanWikiContent(pageContent.value))
})

const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')

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
  if (!path) return
  selectedPath.value = path
  pageLoading.value = true
  try {
    const res = await loadWikiPage(path)
    pageContent.value = res.content || ''
  } finally {
    pageLoading.value = false
  }
}

const loadInitialPage = async () => {
  selectedPath.value = ''
  pageContent.value = ''
  await load()
  const first = pages.value.find(page => page.path === 'index.md') || pages.value[0]
  if (first) await selectPage(first.path)
}

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
  loadInitialPage()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.simulationId, () => {
  loadInitialPage()
})
</script>

<style scoped>
.wiki-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(6px);
}

.wiki-drawer {
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

.wiki-shell-enter-active,
.wiki-shell-leave-active {
  transition: opacity 180ms ease;
}

.wiki-shell-enter-from,
.wiki-shell-leave-to {
  opacity: 0;
}

.wiki-shell-enter-active .wiki-drawer,
.wiki-shell-leave-active .wiki-drawer {
  transition:
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease;
}

.wiki-shell-enter-from .wiki-drawer {
  opacity: 0.82;
  transform: translateX(42px);
}

.wiki-shell-leave-to .wiki-drawer {
  opacity: 0.74;
  transform: translateX(48px);
}

.wiki-drawer-header {
  min-height: 86px;
  padding: 20px 22px 18px;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  animation: wiki-soft-rise 280ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.drawer-kicker {
  display: block;
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.wiki-drawer-header h2 {
  margin: 5px 0 0;
  color: #0F172A;
  font-size: 26px;
  font-weight: 850;
  line-height: 1.06;
}

.wiki-drawer-header p {
  margin: 6px 0 0;
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
  display: grid;
  place-items: center;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.close-btn:hover {
  background: #F8FAFC;
  border-color: #94A3B8;
  color: #0F172A;
  transform: translateY(-1px);
}

.quick-pages {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid #E2E8F0;
  animation: wiki-soft-rise 300ms cubic-bezier(0.22, 1, 0.36, 1) 45ms both;
}

.quick-page {
  min-width: 0;
  border: 1px solid #D8DEE8;
  border-radius: 8px;
  background: #FFFFFF;
  padding: 10px;
  color: #334155;
  text-align: left;
  cursor: pointer;
  transition:
    background 170ms ease,
    border-color 170ms ease,
    box-shadow 170ms ease,
    color 170ms ease,
    transform 170ms ease;
}

.quick-page:hover:not(.disabled) {
  border-color: #CBD5E1;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.07);
  transform: translateY(-1px);
}

.quick-page.active {
  background: #0F172A;
  border-color: #0F172A;
  color: #FFFFFF;
}

.quick-page.disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.quick-page span,
.quick-page strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-page span {
  font-size: 11px;
  font-weight: 850;
}

.quick-page strong {
  margin-top: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 750;
}

.wiki-drawer-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
}

.wiki-nav {
  min-height: 0;
  overflow-y: auto;
  border-right: 1px solid #E2E8F0;
  background: rgba(255, 255, 255, 0.9);
  padding: 18px;
  animation: wiki-soft-rise 320ms cubic-bezier(0.22, 1, 0.36, 1) 80ms both;
}

.nav-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.nav-heading span {
  color: #0F172A;
  font-size: 15px;
  font-weight: 850;
}

.nav-heading strong {
  padding: 4px 8px;
  border: 1px solid #E2E8F0;
  border-radius: 999px;
  color: #334155;
  background: #F8FAFC;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.wiki-empty,
.reader-empty {
  color: #64748B;
  font-size: 13px;
  line-height: 1.5;
}

.tree-group {
  margin-bottom: 18px;
}

.tree-group h3 {
  margin: 0 0 8px;
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.tree-item {
  width: 100%;
  min-width: 0;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  padding: 9px 10px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  color: #334155;
  text-align: left;
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.tree-item:hover {
  background: #F8FAFC;
  border-color: #E2E8F0;
  transform: translateX(2px);
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
  padding: 24px;
  animation: wiki-soft-rise 340ms cubic-bezier(0.22, 1, 0.36, 1) 110ms both;
}

.reader-empty,
.reader-article-frame {
  max-width: 820px;
  margin: 0 auto;
}

.reader-header {
  padding: 22px 24px;
  border: 1px solid #D8DEE8;
  border-bottom: 0;
  border-radius: 10px 10px 0 0;
  background: #FFFFFF;
}

.reader-header span {
  display: block;
  color: #64748B;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.reader-header h1 {
  margin: 5px 0 0;
  color: #0F172A;
  font-size: 28px;
  font-weight: 850;
  line-height: 1.08;
}

.reader-header p {
  margin: 8px 0 0;
  color: #64748B;
  font-size: 13px;
  font-weight: 650;
}

.reader-empty,
.markdown-body {
  border: 1px solid #D8DEE8;
  border-radius: 10px;
  background: #FFFFFF;
  padding: 26px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.reader-header + .markdown-body {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.markdown-body {
  color: #1E293B;
  font-size: 15px;
  line-height: 1.68;
}

.wiki-page-enter-active,
.wiki-page-leave-active {
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}

.wiki-page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.wiki-page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
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

@keyframes wiki-soft-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 840px) {
  .wiki-overlay {
    justify-content: stretch;
    background: #FFFFFF;
  }

  .wiki-drawer {
    width: 100%;
    min-width: 100vw;
    box-shadow: none;
  }

  .quick-pages {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .wiki-drawer-body {
    grid-template-columns: 1fr;
  }

  .wiki-nav {
    max-height: 220px;
    border-right: 0;
    border-bottom: 1px solid #E2E8F0;
  }

  .wiki-reader {
    padding: 18px;
  }

  .reader-header h1 {
    font-size: 23px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .wiki-shell-enter-active,
  .wiki-shell-leave-active,
  .wiki-shell-enter-active .wiki-drawer,
  .wiki-shell-leave-active .wiki-drawer,
  .wiki-page-enter-active,
  .wiki-page-leave-active,
  .quick-page,
  .tree-item,
  .close-btn {
    transition: none;
  }

  .wiki-drawer-header,
  .quick-pages,
  .wiki-nav,
  .wiki-reader {
    animation: none;
  }

  .wiki-shell-enter-from .wiki-drawer,
  .wiki-shell-leave-to .wiki-drawer,
  .wiki-page-enter-from,
  .wiki-page-leave-to,
  .quick-page:hover:not(.disabled),
  .tree-item:hover,
  .close-btn:hover {
    transform: none;
  }
}
</style>
