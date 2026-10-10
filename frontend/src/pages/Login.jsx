import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Compass, Loader2 } from "lucide-react"
import { data } from "../lib/data.js"
import { useToast } from "../components/Toast.jsx"

export default function Login() {
  const navigate = useNavigate()
  const toast = useToast()
  const [mode, setMode] = useState("login") // login | register
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    try {
      if (mode === "login") {
        await data.login(username, password)
      } else {
        await data.register(username, email, password)
        await data.login(username, password)
      }
      toast({ type: "success", title: "Welcome back, Naturalist!" })
      navigate("/", { replace: true })
    } catch (err) {
      toast({ type: "error", title: "Could not sign in", message: err.message })
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
            {["login", "register"].map((m) => (
              <button key={m} onClick={() => setMode(m)} className={`flex-1 py-2 rounded-lg font-semibold ${mode === m ? "bg-nat-forest text-nat-bg shadow-sm" : "text-nat-muted"}`}>
                {m === "login" ? "Sign in" : "Register"}
              </button>
            ))}
          </div>
          <form onSubmit={submit} className="space-y-2.5 pt-2">
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            {mode === "register" && <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />}
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="w-full px-3 py-2.5 bg-nat-bg border border-nat-border rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-nat-forest" />
            <button disabled={busy || !username || !password} className="w-full py-3 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md flex items-center justify-center gap-2 disabled:opacity-50">
              {busy && <Loader2 className="w-4 h-4 animate-spin" />} {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}