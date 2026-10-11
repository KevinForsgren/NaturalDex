import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { data } from "../lib/data.js"

const AuthCtx = createContext(null)

export function useAuth() {
  return useContext(AuthCtx)
}

export default function AuthProvider({ children }) {
  const [status, setStatus] = useState("loading") // loading | authed | anonymous
  const [user, setUser] = useState(null)

  useEffect(() => {
    let alive = true
    data.restoreSession()
      .then(({ user }) => { if (alive) { setUser(user); setStatus("authed") } })
      .catch(() => { if (alive) { setUser(null); setStatus("anonymous") } })
    return () => { alive = false }
  }, [])

  const login = useCallback(async (username, password) => {
    const res = await data.login(username, password)
    const u = res && res.user ? res.user : { username }
    setUser(u)
    setStatus("authed")
    return u
  }, [])

  const register = useCallback(async (username, email, password) => {
    await data.register(username, email, password)
    const res = await data.login(username, password)
    const u = res && res.user ? res.user : { username }
    setUser(u)
    setStatus("authed")
    return u
  }, [])

  const logout = useCallback(async () => {
    try { await data.logout() } catch (_) { /* session may already be gone */ }
    setUser(null)
    setStatus("anonymous")
  }, [])

  const refresh = useCallback(async () => {
    try {
      const { user } = await data.restoreSession()
      setUser(user)
      setStatus("authed")
      return user
    } catch (_) {
      setUser(null)
      setStatus("anonymous")
      return null
    }
  }, [])

  return (
    <AuthCtx.Provider value={{ status, user, login, register, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  )
}