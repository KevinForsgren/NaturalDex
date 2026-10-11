// Real FastAPI backend client for NaturalDex.
//
// Thin, transport-agnostic HTTP wrappers around the backend contract. React uses
// it via fetch with a persistent HttpOnly cookie (same-origin through the Vite
// proxy); a React Native client can call the same functions passing the JWT as
// `auth` (Bearer header) instead of relying on browser cookies.
//
// Every request has a timeout so a slow/unreachable backend cannot leave the UI
// on a loading state indefinitely, and Pydantic 422 validation details are
// surfaced as readable messages instead of a generic "Request failed".

const BASE = import.meta.env.VITE_API_URL || "/api"
const TIMEOUT_MS = 15000

function codeOf(status) {
  const fallback =
    status === 401 ? "UNAUTHORIZED"
    : status === 403 ? "FORBIDDEN"
    : status === 404 ? "NOT_FOUND"
    : status === 422 ? "VALIDATION_ERROR"
    : status === 429 ? "RATE_LIMITED"
    : "REQUEST_FAILED"
  return fallback
}

function messageOf(detail, status) {
  if (typeof detail === "string" && detail) return detail
  if (detail && typeof detail === "object") {
    if (typeof detail.message === "string" && detail.message) return detail.message
    if (Array.isArray(detail)) {
      // FastAPI/Pydantic 422 detail is a list of {loc, msg, type}.
      return detail.map((d) => {
        const where = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : ""
        return where ? `${where}: ${d.msg}` : d.msg
      }).join("; ")
    }
    if (detail.msg) return detail.msg
  }
  if (status === 422) return "The request could not be validated. Check the submitted data."
  if (status === 401) return "Incorrect username or password."
  return "Request failed. Please try again."
}

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

  const controller = typeof AbortController !== "undefined" ? new AbortController() : null
  const timer = controller ? setTimeout(() => controller.abort(), TIMEOUT_MS) : null
  let res
  try {
    res = await fetch(url, { ...opts, signal: controller ? controller.signal : undefined })
  } catch (err) {
    if (err && err.name === "AbortError") {
      throw new ApiError(0, "NETWORK_TIMEOUT", "The request timed out. Please try again.")
    }
    throw new ApiError(0, "NETWORK_ERROR", err && err.message ? err.message : "Network error. Check that the backend is running.")
  } finally {
    if (timer) clearTimeout(timer)
  }

  const text = await res.text()
  let body = null
  try { body = text ? JSON.parse(text) : null } catch (_) { body = text }
  if (!res.ok) {
    const detail = body && body.detail !== undefined ? body.detail : null
    throw new ApiError(res.status, codeOf(res.status), messageOf(detail, res.status))
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
  card: (publicId, auth) => req("GET", `/collection/card-${publicId}`, { auth }),

  // Discovery
  createDiscovery: (payload, auth) => req("POST", "/discoveries", { json: payload, auth }),
  uploadPhoto: (discoveryId, order, blob, contentType, auth) => {
    const form = new FormData()
    form.append("file", new File([blob], `view-${order}.jpg`, { type: contentType }))
    return req("POST", `/discoveries/${discoveryId}/photos`, { form, auth, query: { order } })
  },
  submitDiscovery: (discoveryId, auth) => req("POST", `/discoveries/${discoveryId}/submit`, { auth }),

  // Home base / pairing
  pairingChallenge: (auth) => req("POST", "/home-base/pairing-challenge", { auth }),
  pair: (token, name, auth) => req("POST", "/home-base/pair", { json: { token, name }, auth }),
  verifyPairing: (challenge, auth) => req("POST", "/home-base/verify-pairing", { json: { challenge }, auth }),
  homeBaseStatus: (auth) => req("GET", "/home-base/status", { auth }),
  revokeHomeBase: (id, auth) => req("POST", `/home-base/${id}/revoke`, { auth }),

  // Journal
  journal: (auth) => req("GET", "/journal", { auth }),

  // Profile
  profileStats: (auth) => req("GET", "/profile/stats", { auth }),
}

export default api