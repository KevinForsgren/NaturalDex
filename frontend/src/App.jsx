import React from "react"
import { Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom"
import { Compass, Loader2, Laptop } from "lucide-react"
import ToastProvider, { useToast } from "./components/Toast.jsx"
import BottomNav from "./components/BottomNav.jsx"
import Home from "./pages/Home.jsx"
import Collection from "./pages/Collection.jsx"
import CardDetail from "./pages/CardDetail.jsx"
import Journal from "./pages/Journal.jsx"
import Profile from "./pages/Profile.jsx"
import Discover from "./pages/Discover.jsx"
import Login from "./pages/Login.jsx"
import AuthProvider, { useAuth } from "./state/AuthContext.jsx"

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
  if (status === "loading") return <LoadingScreen />
  if (status !== "authed") return <Navigate to="/login" replace state={{ from: location }} />

  const displayName = user && (user.username || user.name) ? user.username || user.name : "Explorer"

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
            onClick={() => toast({ title: "Edge AI", message: "Home base connected — local identification ready." })}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-nat-sage/60 border border-nat-border text-xs font-medium text-nat-forest hover:bg-nat-sage transition-all"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
            <span className="text-[11px]">Edge AI Ready</span>
            <Laptop className="w-3.5 h-3.5 ml-0.5 text-nat-muted" />
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