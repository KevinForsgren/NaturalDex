// Real FastAPI backend client for NaturalDex.
//
// Thin, transport-agnostic HTTP wrappers around the backend contract. React uses
// it via fetch with same-origin cookies; a React Native client can call the same
// functions passing the JWT as `auth` (Bearer header) instead of relying on
// browser cookies.

const BASE = import.meta.env.VITE_API_URL || "/api"

async function req(method, path, { json, form, auth, query } = {}) {
  let url = `${BASE}${path}`
  if (query) {
    const qs = new URLSearchParams(
      Object.entries(query).filter(([, v]) => v !== undefined && v !== null)
    ).toString()
    if (qs) url += `?${qs}`
  }
  const headers = {}
  const opts = { method, headers, credentials: "include" }
  if (auth) headers.Authorization = `Bearer ${auth}`
  if (form) {
    opts.body = form
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json"
    opts.body = JSON.stringify(json)
  }
  const res = await fetch(url, opts)
  const text = await res.text()
  let body = null
  try { body = text ? JSON.parse(text) : null } catch (_) { body = text }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : null
    throw new ApiError(res.status, detail && detail.code ? detail.code : "REQUEST_FAILED", detail && detail.message ? detail.message : (body && typeof body === "string" ? body : "Request failed"))
  }
  return body
}

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

export const api = {
  // Auth
  register: (payload) => req("POST", "/auth/register", { json: payload }),
  login: (payload) => req("POST", "/auth/login", { json: payload }),
  logout: () => req("POST", "/auth/logout"),
  me: () => req("GET", "/auth/me"),
  setTimezone: (timezone, auth) => req("PUT", "/profile/timezone", { json: { timezone }, auth }),

  // Daily tasks
  dailyTasks: (auth) => req("GET", "/daily-tasks", { auth }),
  dailyTaskHistory: (auth) => req("GET", "/daily-tasks/history", { auth }),

  // Collection
  collection: (category, auth) => req("GET", "/collection", { query: { category }, auth }),
  card: (publicId, auth) =>
    req("GET", `/collection/card-${publicId}`, { auth }),

  // Discovery
  createDiscovery: (payload, auth) => req("POST", "/discoveries", { json: payload, auth }),
  uploadPhoto: (discoveryId, order, blob, contentType, auth) => {
    const form = new FormData()
    form.append("file", new File([blob], `view-${order}.jpg`, { type: contentType }))
    return req("POST", `/discoveries/${discoveryId}/photos`, {
      form,
      auth,
      query: { order },
    })
  },
  submitDiscovery: (discoveryId, auth) =>
    req("POST", `/discoveries/${discoveryId}/submit`, { auth }),

  // Home base / pairing
  pairingChallenge: (auth) => req("POST", "/home-base/pairing-challenge", { auth }),
  pair: (token, name, auth) => req("POST", "/home-base/pair", { json: { token, name }, auth }),
  homeBaseStatus: (auth) => req("GET", "/home-base/status", { auth }),
  revokeHomeBase: (id, auth) => req("POST", `/home-base/${id}/revoke`, { auth }),

  // Journal
  journal: (auth) => req("GET", "/journal", { auth }),

  // Profile
  profileStats: (auth) => req("GET", "/profile/stats", { auth }),
}

export default api