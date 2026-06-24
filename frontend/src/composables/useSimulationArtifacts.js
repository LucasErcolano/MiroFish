import { ref, shallowRef } from 'vue'
import {
  getSimulationArtifacts,
  getSimulationWiki,
  getSimulationWikiPage,
  getSimulationTelemetry,
  getSimulationRoutingAudit,
  listFusionVerdicts,
  getFusionVerdict
} from '../api/simulation'

export function useSimulationArtifacts(simulationId) {
  const manifest = shallowRef(null)
  const wiki = shallowRef(null)
  const telemetry = shallowRef(null)
  const audit = shallowRef(null)
  const verdicts = shallowRef([])
  const loading = ref(false)
  const error = ref(null)

  const resolveId = () => typeof simulationId === 'function' ? simulationId() : simulationId

  const load = async () => {
    const id = resolveId()
    if (!id) return
    loading.value = true
    error.value = null
    try {
      const artifactRes = await getSimulationArtifacts(id)
      manifest.value = artifactRes
      const jobs = []
      if (artifactRes.wiki) jobs.push(getSimulationWiki(id).then(res => { wiki.value = res }))
      if (artifactRes.telemetry) jobs.push(getSimulationTelemetry(id).then(res => { telemetry.value = res }))
      if (artifactRes.audit) jobs.push(getSimulationRoutingAudit(id).then(res => { audit.value = res }))
      jobs.push(listFusionVerdicts(id).then(res => { verdicts.value = res.verdicts || [] }).catch(() => { verdicts.value = [] }))
      await Promise.all(jobs)
    } catch (err) {
      error.value = err?.message || String(err)
    } finally {
      loading.value = false
    }
  }

  const loadWikiPage = async (path) => {
    return getSimulationWikiPage(resolveId(), path)
  }

  const loadFusionVerdict = async (path) => {
    return getFusionVerdict(resolveId(), path)
  }

  return {
    manifest,
    wiki,
    telemetry,
    audit,
    verdicts,
    loading,
    error,
    load,
    loadWikiPage,
    loadFusionVerdict
  }
}
