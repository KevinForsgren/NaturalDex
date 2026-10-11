import React, { useEffect, useState } from "react"
import { Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom"
import { Compass, Loader2, Laptop, Wifi, WifiOff } from "lucide-react"
import ToastProvider, { useToast } from "./components/Toast.jsx"
import BottomNav from "./components/BottomNav.jsx"
import Home from "./pages/Home.jsx"
import Collection from "./pages/Collection.jsx"
import CardDetail from "./pages/CardDetail.jsx"
import Journal from "./pages/Journal.jsx"
import Profile from "./pages/Profile.jsx"
import Discover from "./pages/Discover.jsx"
import Login from "./pages/Login.jsx"
import PairingPage from "./pages/PairingPage.jsx"
import AuthProvider, { useAuth } from "./state/AuthContext.jsx"
import { data } from "./lib/data.js"

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-nat-bg flex flex-col items-center justify-center gap-3">
      <div className="w-14 h-14 rounded-2xl bg-nat-forest text-nat-bg flex items-center justify-center shadow-paper-lg">
        <Compass className="w-7 h-7" />
      </div>
      <Loader2 className="w-5 h-5 text-nat-forest animate-spin" />
    </div>
  )
}

function Shell() {
  const { status, user } = useAuth()
  const location = useLocation()
  const toast = useToast()
  const [hbStatus, setHbStatus] = useState(null)

  if (status === "loading") return <LoadingScreen />
  if (status !== "authed") return <Navigate to="/login" replace state={{ from: location }} />

  const displayName = user && (user.username || user.name) ? user.username || user.name : "Explorer"

  // Fetch home base status on mount and poll periodically
  useEffect(() => {
    let alive = true
    let pollInterval = null

    const fetchStatus = () => {
      data.homeBaseStatus().then((s) => {
        if (alive) setHbStatus(s)
      }).catch(() => {})
    }

    fetchStatus()
    pollInterval = setInterval(fetchStatus, 30000) // Poll every 30 seconds

    // Listen for pairing completion events
    const handlePairingComplete = () => fetchStatus()
    window.addEventListener('homebase-paired', handlePairingComplete)

    return () => {
      alive = false
      if (pollInterval) clearInterval(pollInterval)
      window.removeEventListener('homebase-paired', handlePairingComplete)
    }
  }, [])

  const isPaired = hbStatus?.paired && hbStatus?.model_ready
  const isConnected = hbStatus?.paired

  return (
    <div className="min-h-screen flex flex-col items-center antialiased selection:bg-nat-sage selection:text-nat-forest">
      <div className="w-full max-w-md min-h-screen flex flex-col justify-between bg-nat-bg border-x border-nat-border/50 shadow-2xl relative overflow-hidden pb-20">
        <header className="sticky top-0 z-30 bg-nat-bg/90 backdrop-blur-md border-b border-nat-border px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-nat-forest flex items-center justify-center text-nat-bg shadow-sm">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-serif font-bold text-lg leading-none text-nat-forest tracking-tight">NatureDex</h1>
              <span className="text-[10px] uppercase font-semibold text-nat-muted tracking-wider">Field Journal</span>
            </div>
          </div>
          <button
            onClick={() => toast({ 
              title: "Edge AI", 
              message: isPaired 
                ? "Home base connected — local identification ready." 
                : isConnected 
                  ? "Home base paired but model not ready. Check Ollama on laptop." 
                  : "No home base paired. Go to Profile to pair your laptop."
            })}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-all ${
              isPaired 
                ? "bg-emerald-50 border-emerald-200 text-emerald-700" 
                : isConnected 
                  ? "bg-amber-50 border-amber-200 text-amber-700" 
                  : "bg-nat-sage/60 border-nat-border text-nat-forest"
            }`}
          >
            <span className={`w-2 h-2 rounded-full animate-pulse ${isPaired ? "bg-emerald-600" : isConnected ? "bg-amber-500" : "bg-nat-muted"}`} />
            <span className="text-[11px]">{isPaired ? "Edge AI Ready" : isConnected ? "Model Offline" : "Not Paired"}</span>
            {isPaired ? <Wifi className="w-3.5 h-3.5 ml-0.5 text-emerald-600" /> : isConnected ? <WifiOff className="w-3.5 h-3.5 ml-0.5 text-amber-500" /> : <Laptop className="w-3.5 h-3.5 ml-0.5 text-nat-muted" />}
          </button>
        </header>

        <Outlet context={{ user, displayName }} />
        <BottomNav />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/pair/:challenge" element={<PairingPage />} />
          <Route element={<Shell />}>
            <Route path="/" element={<Home />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/collection/card-:publicId" element={<CardDetail />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ToastProvider>
  )
}