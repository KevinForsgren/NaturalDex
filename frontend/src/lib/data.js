// App-facing data facade.
//
// Pages only import from this module, so the UI is agnostic to whether data
// comes from the in-browser demo store or the real FastAPI backend. This keeps
// shared business logic out of the React components and lets a future
// React Native + Expo frontend reuse the same contract.

import { api } from "./api"
import demo from "./demo"

const TOKEN_KEY = "ndx-auth-token"
const backendEnabled = () => import.meta.env.VITE_USE_BACKEND === "1"
const isDemo = () => !backendEnabled()

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || null } catch (_) { return null }
}
function setToken(t) {
  try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY) } catch (_) {}
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result)
    r.onerror = reject
    r.readAsDataURL(blob)
  })
}

export const data = {
  mode: () => (isDemo() ? "demo" : "backend"),
  isDemo,

  // ---- auth (backend only; demo is anonymous) ----
  async login(username, password) {
    const res = await api.login({ username, password })
    setToken(res.access_token)
    return res
  },
  async register(username, email, password) {
    const res = await api.register({ username, email, password })
    return res
  },
  async logout() {
    if (!isDemo()) { try { await api.logout() } catch (_) {} }
    setToken(null)
  },
  hasSession() {
    return isDemo() || !!getToken()
  },

  // ---- daily tasks ----
  async dailyTasks() {
    if (isDemo()) return demo.getDailyTasks()
    return api.dailyTasks(getToken())
  },

  // ---- collection ----
  async collection(category) {
    if (isDemo()) return demo.listCollection(category)
    return api.collection(category, getToken())
  },
  async card(publicId) {
    if (isDemo()) {
      const card = demo.getCardBySpecies(publicId)
      return { card: card ? toCardDetail(card) : null }
    }
    return api.card(publicId, getToken())
  },

  // ---- profile ----
  async profile() {
    if (isDemo()) return demo.getProfileStats()
    return api.profileStats(getToken())
  },

  // ---- discovery ----
  // blobs: array of 3 { order, blob, contentType }. Returns a normalized result.
  async discover({ blobs, categoryHint }) {
    if (isDemo()) {
      const created = demo.createDiscovery()
      blobs.forEach((p) => demo.uploadPhoto(p.dataUrl))
      const res = demo.submitDiscovery()
      return {
        accepted: res.accepted,
        status: res.status,
        isDemo: true,
        isFirstDiscovery: res.isFirstDiscovery,
        count: res.count,
        cardPublicId: res.cardPublicId,
        cardUrl: res.cardUrl,
        taskProgress: res.taskProgress,
        specimen: {
          commonName: res.demoResult.commonName,
          scientificName: res.demoResult.scientificName,
          category: res.demoResult.category,
          rarity: res.demoResult.rarity,
          confidence: res.demoResult.confidence,
          xp: res.demoResult.xp,
          summary: res.demoResult.summary,
        },
      }
    }

    const token = getToken()
    const created = await api.createDiscovery({ category_hint: categoryHint, idempotency_key: crypto.randomUUID() }, token)
    const did = created.discovery.id
    for (const p of blobs.sort((a, b) => a.order - b.order)) {
      await api.uploadPhoto(did, p.order, p.blob, p.contentType, token)
    }
    const res = await api.submitDiscovery(did, token)

    if (!res || res.accepted === false) {
      return { accepted: false, status: res.status, errorCode: res.errorCode, errorMessage: res.message, isDemo: false }
    }

    let cardDetail = null
    try {
      const c = await api.card(res.cardPublicId, token)
      cardDetail = c && c.card ? c.card : null
    } catch (_) { /* optional enrichment */ }
    const sp = cardDetail ? cardDetail.species : (res.discovery && res.discovery.species) || {}
    return {
      accepted: true,
      status: "accepted",
      isDemo: false,
      isFirstDiscovery: res.isFirstDiscovery,
      count: res.count,
      cardPublicId: res.cardPublicId,
      cardUrl: res.cardUrl,
      specimen: {
        commonName: sp.common_name || (res.discovery && res.discovery.identification_label),
        scientificName: sp.scientific_name,
        category: sp.category,
        rarity: sp.rarity,
        confidence: res.discovery && res.discovery.identification_confidence,
        xp: res.isFirstDiscovery ? 30 : 15,
        summary: res.discovery && res.discovery.summary,
      },
    }
  },
}

function toCardDetail(sp) {
  return {
    public_id: sp.id,
    count: sp.scanCount || 1,
    species: {
      canonical_key: sp.id,
      common_name: sp.commonName,
      scientific_name: sp.scientificName,
      category: sp.category,
      rarity: sp.rarity,
      description: sp.botanicalDetails || sp.notes || null,
      hint: sp.hint || null,
    },
  }
}

export default data