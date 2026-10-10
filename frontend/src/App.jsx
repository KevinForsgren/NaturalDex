import React from "react"
import { Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom"
import { Compass, Laptop } from "lucide-react"
import ToastProvider from "./components/Toast.jsx"
import BottomNav from "./components/BottomNav.jsx"
import Home from "./pages/Home.jsx"
import Collection from "./pages/Collection.jsx"
import CardDetail from "./pages/CardDetail.jsx"
import Journal from "./pages/Journal.jsx"
import Profile from "./pages/Profile.jsx"
import Discover from "./pages/Discover.jsx"
import Login from "./pages/Login.jsx"
import { data } from "./lib/data.js"
import { useToast } from "./components/Toast.jsx"

function Shell() {
  // In backend mode, unauthenticated users are sent to /login. Demo is anonymous.
  const authed = data.hasSession()
  const location = useLocation()
  const toast = useToast()
  if (!authed) return <Navigate to="/login" replace state={{ from: location }} />

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
          <div className="flex items-center gap-2">
            <button onClick={() => toast({ title: "Edge AI", message: data.isDemo() ? "Demo home base — simulated pairing." : "Home base connected." })} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-nat-sage/60 border border-nat-border text-xs font-medium text-nat-forest hover:bg-nat-sage transition-all">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span className="text-[11px]">{data.isDemo() ? "Demo AI" : "Edge AI Ready"}</span>
              <Laptop className="w-3.5 h-3.5 ml-0.5 text-nat-muted" />
            </button>
          </div>
        </header>

        <Outlet />
        <BottomNav />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/discover" element={<Discover />} />
        <Route path="/login" element={<Login />} />
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/collection" element={<Collection />} />
          <Route path="/collection/card-:publicId" element={<CardDetail />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  )
}