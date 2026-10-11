import React, { useState } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { Compass, Loader2, AlertTriangle, ShieldCheck } from "lucide-react"
import { useAuth } from "../state/AuthContext.jsx"

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const auth = useAuth()
  const [mode, setMode] = useState("login") // login | register
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const from = location.state && location.state.from ? location.state.from.pathname : "/"

  function validate() {
    if (!username.trim() || !password) return "Please enter a username and password."
    if (password.length < 8) return "Password must be at least 8 characters."
    if (mode === "register") {
      if (!/\S+@\S+\.\S+/.test(email)) return "Enter a valid email address."
      if (password !== confirm) return "Passwords do not match."
    }
    return null
  }

  async function submit(e) {
    e.preventDefault()
    const problem = validate()
    if (problem) { setError(problem); return }
    setBusy(true)
    setError(null)
    try {
      if (mode === "login") await auth.login(username.trim(), password)
      else await auth.register(username.trim(), email.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err && err.message ? err.message : "Something went wrong. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-nat-bg paper-texture flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-nat-forest text-nat-bg flex items-center justify-center shadow-paper-lg">
            <Compass className="w-7 h-7" />
          </div>
          <h1 className="font-serif text-2xl font-bold text-nat-forest">NatureDex</h1>
          <p className="text-xs text-nat-muted">Sign in to open your Field Journal</p>
        </div>

        <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 shadow-paper space-y-2">
          <div className="flex rounded-xl bg-nat-sage p-0.5 text-xs">
            <button onClick={() => { setMode("login"); setError(null) }} className={`flex-1 py-2 rounded-lg font-semibold ${mode === "login" ? "bg-nat-forest text-nat-bg shadow-sm" : "text-nat-muted"}`}>Sign in</button>
            <button onClick={() => { setMode("register"); setError(null) }} className={`flex-1 py-2 rounded-lg font-semibold ${mode === "register" ? "bg-nat-forest text-nat-bg shadow-sm" : "text-nat-muted"}`}>Register</button>
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-nat-clay/10 border border-nat-clay/30 text-nat-text rounded-xl p-2.5 text-xs">
              <AlertTriangle className="w-4 h-4 text-nat-clay shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={submit} className="space-y-2.5 pt-2">
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" autoCapitalize="none" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            {mode === "register" && (
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            )}
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            {mode === "register" && (
              <input value={confirm} onChange={(e) => setConfirm(e.target.value)} type="password" placeholder="Confirm password" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            )}
            <button disabled={busy || !username || !password} className="w-full py-3 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md flex items-center justify-center gap-2 disabled:opacity-50">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />} {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="flex items-center justify-center gap-1.5 text-[10px] text-nat-muted pt-1">
            <ShieldCheck className="w-3.5 h-3.5 text-nat-clay" /> Your session stays private on this device.
          </p>
        </div>
      </div>
    </div>
  )
}