// App-facing data facade. All data is read/written through the real backend;
// there is no in-browser mock for user activity. Session state is an HttpOnly
// cookie set by the backend, so credentialed requests carry it automatically.
// The functions are transport-agnostic so a React Native + Expo client can call
// the same backend contracts.

import { api } from "./api"

export const data = {
  // ---- auth ----
  async login(username, password) {
    return api.login({ username, password })
  },
  async register(username, email, password) {
    return api.register({ username, email, password })
  },
  async logout() {
    return api.logout()
  },
  // Restore the current session on app load. Returns the user or throws 401.
  async restoreSession() {
    const res = await api.me()
    const user = res && res.user ? res.user : null
    return { user }
  },
  async setTimezone(timezone) {
    return api.setTimezone(timezone)
  },

  // ---- daily tasks ----
  dailyTasks: () => api.dailyTasks(),

  // ---- collection ----
  collection: (category) => api.collection(category),
  card: (publicId) => api.card(publicId),

  // ---- journal / profile ----
  journal: () => api.journal(),
  profile: () => api.profileStats(),

  // ---- home base / pairing ----
  pairingChallenge: () => api.pairingChallenge(),
  verifyPairing: (challenge) => api.verifyPairing(challenge),
  homeBaseStatus: () => api.homeBaseStatus(),
  revokeHomeBase: (id) => api.revokeHomeBase(id),

  // ---- discovery ----
  // blobs: array of { order, blob, contentType }. Returns a normalized result.
  async discover({ blobs, categoryHint }) {
    const idempotencyKey = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const created = await api.createDiscovery({
      category_hint: categoryHint || undefined,
      idempotency_key: idempotencyKey,
    })
    const did = created.discovery.id
    for (const p of [...blobs].sort((a, b) => a.order - b.order)) {
      await api.uploadPhoto(did, p.order, p.blob, p.contentType)
    }
    const res = await api.submitDiscovery(did)

    if (!res || res.accepted === false) {
      return {
        accepted: false,
        status: res && res.status,
        errorCode: (res && res.errorCode) || "IDENTIFICATION_UNCERTAIN",
        errorMessage: (res && res.message) || "We couldn't verify these photos. Please try again with three clear views.",
      }
    }

    const d = res.discovery || {}
    const sp = d.species || {}
    // Enrich with rarity/description from the card when available.
    let rarity = null
    let description = null
    try {
      const c = await api.card(res.cardPublicId)
      if (c && c.card) {
        rarity = c.card.species && c.card.species.rarity
        description = c.card.species && c.card.species.description
      }
    } catch (_) { /* optional enrichment */ }

    return {
      accepted: true,
      status: "accepted",
      isFirstDiscovery: res.isFirstDiscovery,
      count: res.count,
      cardPublicId: res.cardPublicId,
      cardUrl: res.cardUrl,
      specimen: {
        commonName: sp.common_name || d.identification_label || "Unknown specimen",
        scientificName: sp.scientific_name || null,
        category: sp.category || d.category_hint || null,
        rarity: rarity || sp.rarity || "Common",
        confidence: d.identification_confidence != null ? d.identification_confidence * 100 : null,
        xp: res.isFirstDiscovery ? 30 : 15,
        summary: d.summary || (res.isFirstDiscovery ? "A new species added to your field journal." : description),
      },
    }
  },
}

export default data