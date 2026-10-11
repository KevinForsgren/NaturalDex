import React, { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { QRCodeSVG } from "qrcode.react"
import { LogOut, Laptop, ShieldCheck, Download, ChevronRight, Loader2, AlertTriangle, RefreshCw, CheckCircle2, Monitor, Smartphone, Wifi, Check, Camera, QrCode } from "lucide-react"
import { data } from "../lib/data.js"
import { useAuth } from "../state/AuthContext.jsx"
import { useToast } from "../components/Toast.jsx"
import Modal from "../components/Modal.jsx"
import QRScanner from "../components/QRScanner.jsx"

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [hb, setHb] = useState(null)
  const [pairOpen, setPairOpen] = useState(false)
  // pairing state: idle | challenge_ready | scanning | verifying | paired | error
  const [pairing, setPairing] = useState({ state: "idle", token: null, challenge: null, laptopUrl: null, expiresAt: null, error: null, modelReady: false })

  useEffect(() => {
    let alive = true
    data.profile().then((p) => alive && setStats(p)).catch(() => setStats(null))
    data.homeBaseStatus().then((s) => alive && setHb(s)).catch(() => {})
    return () => { alive = false }
  }, [pairOpen])

  const loadStats = useCallback(() => {
    data.profile().then(setStats).catch(() => setStats(null))
  }, [])

  const openPair = useCallback(async () => {
    setPairOpen(true)
    setPairing({ state: "loading", token: null, challenge: null, laptopUrl: null, expiresAt: null, error: null, modelReady: false })
    try {
      const ch = await data.pairingChallenge()
      // Build laptop URL - use current origin but with /home-base/pair path
      // In production, user would use ngrok URL or LAN IP
      const baseUrl = window.location.origin.replace(':3000', ':8000')
      const laptopUrl = `${baseUrl}/home-base/pair?challenge=${ch.token}`
      setPairing({ 
        state: "challenge_ready", 
        token: ch.token, 
        challenge: ch.token,
        laptopUrl,
        expiresAt: ch.expires_at, 
        error: null, 
        modelReady: false 
      })
      data.homeBaseStatus().then(setHb).catch(() => {})
    } catch (err) {
      setPairing({ state: "error", token: null, challenge: null, laptopUrl: null, expiresAt: null, error: err && err.message, modelReady: false })
    }
  }, [])

  const startScan = useCallback(() => {
    setPairing(prev => ({ ...prev, state: "scanning" }))
  }, [])

  const handleScanResult = useCallback(async (result) => {
    // Extract challenge from scanned QR URL
    try {
      const url = new URL(result)
      const challenge = url.searchParams.get('challenge')
      if (challenge) {
        setPairing(prev => ({ ...prev, challenge, state: "verifying" }))
        const res = await data.verifyPairing(challenge)
        if (res.status === "paired") {
          setPairing(prev => ({ 
            ...prev, 
            state: "paired", 
            modelReady: res.model_ready,
            error: null 
          }))
          data.homeBaseStatus().then(setHb).catch(() => {})
          toast({ type: "success", title: "Home Base Paired", message: res.model_ready ? "Local AI model is ready." : "Paired, but model not responding. Check Ollama." })
        } else {
          setPairing(prev => ({ ...prev, state: "error", error: res.message || "Pairing verification failed." }))
        }
      } else {
        setPairing(prev => ({ ...prev, state: "error", error: "Invalid QR code. Scan the QR on your laptop." }))
      }
    } catch (e) {
      setPairing(prev => ({ ...prev, state: "error", error: "Failed to parse QR code." }))
    }
  }, [])

  const verifyPairing = useCallback(async () => {
    if (!pairing.challenge) return
    setPairing(prev => ({ ...prev, state: "verifying" }))
    try {
      const res = await data.verifyPairing(pairing.challenge)
      if (res.status === "paired") {
        setPairing(prev => ({ 
          ...prev, 
          state: "paired", 
          modelReady: res.model_ready,
          error: null 
        }))
        // Refresh home base status
        data.homeBaseStatus().then(setHb).catch(() => {})
        toast({ type: "success", title: "Home Base Paired", message: res.model_ready ? "Local AI model is ready." : "Paired, but model not responding. Check Ollama." })
      } else {
        setPairing(prev => ({ ...prev, state: "error", error: res.message || "Pairing verification failed." }))
      }
    } catch (err) {
      setPairing(prev => ({ ...prev, state: "error", error: err && err.message || "Verification failed." }))
    }
  }, [pairing.challenge])

  const copyLaptopUrl = useCallback(() => {
    if (pairing.laptopUrl) {
      navigator.clipboard.writeText(pairing.laptopUrl)
      toast({ type: "success", title: "Copied", message: "Laptop URL copied to clipboard." })
    }
  }, [pairing.laptopUrl])

  async function doLogout() {
    await logout()
    navigate("/login", { replace: true })
    toast({ type: "success", title: "Signed out", message: "You've been securely logged out." })
  }

  const xp = stats ? stats.xp_total || 0 : 0
  const level = Math.floor(xp / 100) + 1
  const alias = user ? (user.username || user.name || "Naturalist") : "Naturalist"
  const name = stats && stats.unique_species != null ? stats.unique_species : 0

  const hbLabel = !hb ? null : hb.paired && hb.model_ready ? "Connected: Local Ollama" : hb.status === "revoked" ? "Revoked" : hb.status === "paired" ? "Paired — model offline" : "Not paired"

  return (
    <div className="flex-1 p-4 space-y-5 pb-24 animate-fade-in">
      {/* Identity card */}
      <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 shadow-paper space-y-3 relative overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-full bg-nat-forest text-nat-bg font-serif font-bold text-xl flex items-center justify-center border-2 border-nat-golden shadow-sm">
            {alias.charAt(0).toUpperCase()}
          </div>
          <div>
            <h3 className="font-serif font-bold text-lg text-nat-forest">{alias} Naturalist</h3>
            <p className="text-xs text-nat-muted">Outdoor Field Journal</p>
            <span className="inline-block mt-1 px-2 py-0.5 bg-nat-sage/80 border border-nat-border rounded-md text-[10px] font-semibold text-nat-forest">Rank: Level {level} Naturalist</span>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-nat-border/60 text-center text-xs">
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-forest">{stats ? name : "–"}</span><span className="text-nat-muted text-[11px]">Species Logged</span></div>
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-forest">{stats ? (stats.streak_days || 0) : "–"}</span><span className="text-nat-muted text-[11px]">Day Expo. Streak</span></div>
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-clay">{stats ? xp : "–"}</span><span className="text-nat-muted text-[11px]">XP</span></div>
        </div>
      </div>

      {/* Settings */}
      <div className="space-y-3">
        <h4 className="font-serif font-bold text-base text-nat-forest">Field Guide Settings</h4>
        <div className="bg-nat-paper/60 border border-nat-border rounded-xl divide-y divide-nat-border text-xs">
          <div className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5"><ShieldCheck className="w-4 h-4 text-nat-clay" /><div><p className="font-medium text-nat-text">Privacy-Safe Coordinates</p><p className="text-[10px] text-nat-muted">Blur exact GPS on public cards</p></div></div>
            <input type="checkbox" defaultChecked className="accent-nat-forest" />
          </div>
          <button onClick={openPair} className="w-full p-3 flex items-center justify-between text-left hover:bg-nat-sage/30">
            <div className="flex items-center gap-2.5">
              <Laptop className="w-4 h-4 text-nat-forest" />
              <div><p className="font-medium text-nat-text">Laptop-Hosted AI Model</p><p className="text-[10px] text-nat-muted">{hbLabel || "Set up local identification"}</p></div>
            </div>
            <ChevronRight className="w-4 h-4 text-nat-muted" />
          </button>
        </div>
      </div>

      <button onClick={() => { const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), user: alias, stats }, null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "naturedex_field_journal.json"; a.click(); URL.revokeObjectURL(a.href); toast({ type: "success", title: "Journal Exported", message: "Downloaded naturedex_field_journal.json" }) }} className="w-full py-2.5 px-4 bg-nat-sage border border-nat-border text-nat-forest hover:bg-nat-border font-serif font-semibold text-xs rounded-xl transition-all flex items-center justify-center gap-2">
        <Download className="w-4 h-4" /> Export Notebook (JSON)
      </button>

      <button onClick={doLogout} className="w-full py-3 px-4 bg-nat-clay/10 border border-nat-clay/40 text-nat-clay hover:bg-nat-clay/20 font-serif font-bold text-xs rounded-xl flex items-center justify-center gap-2">
        <LogOut className="w-4 h-4" /> Log Out
      </button>

      <Modal open={pairOpen} onClose={() => setPairOpen(false)} title="Home-Base AI Model" accent="text-nat-clay">
        <div className="p-5 space-y-4 text-center">
          <p className="text-xs text-nat-muted leading-relaxed">
            Pair NatureDex with your laptop running Ollama for private, local AI identification.
            <br />
            <span className="font-medium">No cloud — your photos never leave your devices.</span>
          </p>

          <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 flex flex-col items-center gap-3">
            {/* Idle: Generate challenge */}
            {pairing.state === "idle" && (
              <button onClick={openPair} className="w-full px-4 py-2 bg-nat-forest text-nat-bg rounded-xl text-xs font-serif font-bold">
                Generate Pairing Code
              </button>
            )}

            {/* Loading */}
            {pairing.state === "loading" && (
              <div className="h-32 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-nat-forest animate-spin" />
              </div>
            )}

            {/* Challenge ready: Show laptop URL and instructions */}
            {pairing.state === "challenge_ready" && pairing.challenge && pairing.laptopUrl && (
              <>
                <div className="space-y-3 text-left w-full max-w-xs">
                  <div className="flex items-center gap-2 text-xs text-nat-muted">
                    <Monitor className="w-4 h-4" />
                    <span>Open this URL on your laptop:</span>
                  </div>
                  <div className="flex gap-2">
                    <input
                      readOnly
                      value={pairing.laptopUrl}
                      className="flex-1 px-3 py-2 bg-nat-bg border border-nat-border rounded-xl text-[10px] font-mono"
                    />
                    <button
                      onClick={copyLaptopUrl}
                      className="px-3 py-2 bg-nat-sage border border-nat-border rounded-xl text-xs font-medium text-nat-forest hover:bg-nat-border transition"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="text-[10px] text-nat-muted">
                    Make sure your laptop can reach this address (use ngrok or LAN IP if on different networks).
                  </p>
                </div>

                <div className="bg-white p-3 rounded-lg shadow-inner-paper">
                  <QRCodeSVG value={pairing.laptopUrl} size={168} fgColor="#244A35" bgColor="#FFFFFF" level="M" />
                </div>
                <p className="text-[11px] font-mono text-nat-muted break-all max-w-[260px]">{pairing.challenge.slice(0, 20)}...</p>
                <p className="text-[10px] text-nat-muted">Code expires {pairing.expiresAt ? new Date(pairing.expiresAt).toLocaleTimeString() : "shortly"}</p>

                <div className="space-y-2">
                  <p className="text-[11px] text-nat-muted">Laptop will show this QR code. Scan it with your phone:</p>
                  <button
                    onClick={startScan}
                    className="w-full px-4 py-2.5 bg-nat-forest text-nat-bg rounded-xl text-xs font-serif font-bold flex items-center justify-center gap-2"
                  >
                    <QrCode className="w-4 h-4" /> Scan QR on Laptop
                  </button>
                  <button
                    onClick={verifyPairing}
                    className="w-full px-4 py-2 bg-nat-sage border border-nat-border text-nat-forest rounded-xl text-xs font-medium"
                  >
                    Or enter challenge manually
                  </button>
                </div>
              </>
            )}

            {/* Scanning QR with camera */}
            {pairing.state === "scanning" && (
              <div className="space-y-3">
                <div className="h-64 bg-nat-bg rounded-xl relative overflow-hidden">
                  <QRScanner onResult={handleScanResult} />
                </div>
                <p className="text-sm text-nat-muted">Point camera at the QR code on your laptop screen</p>
                <button
                  onClick={() => setPairing(prev => ({ ...prev, state: "challenge_ready" }))}
                  className="w-full px-4 py-2 bg-nat-sage border border-nat-border text-nat-forest rounded-xl text-xs font-medium"
                >
                  Cancel
                </button>
              </div>
            )}

            {/* Verifying */}
            {pairing.state === "verifying" && (
              <div className="space-y-3">
                <div className="h-24 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 text-nat-forest animate-spin" />
                </div>
                <p className="text-sm text-nat-muted">Waiting for verification...</p>
                <p className="text-[11px] text-nat-muted">The laptop page will update automatically once paired.</p>
              </div>
            )}

            {/* Paired successfully */}
            {pairing.state === "paired" && (
              <div className="space-y-3">
                <div className="flex items-center justify-center gap-2 text-nat-forest">
                  <CheckCircle2 className="w-8 h-8" />
                  <span className="font-serif font-bold text-lg">Paired!</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-xs">
                  <Wifi className={`w-4 h-4 ${pairing.modelReady ? "text-emerald-600" : "text-nat-clay"}`} />
                  <span className={pairing.modelReady ? "text-emerald-700 font-medium" : "text-nat-clay"}>
                    {pairing.modelReady ? "Local Ollama model ready" : "Ollama not responding — check laptop"}
                  </span>
                </div>
                <p className="text-[10px] text-nat-muted">You can now use Discover to identify species locally.</p>
              </div>
            )}

            {/* Error */}
            {pairing.state === "error" && (
              <div className="space-y-3">
                <div className="flex items-start gap-2 bg-nat-clay/10 border border-nat-clay/30 rounded-xl p-3 text-left text-xs">
                  <AlertTriangle className="w-4 h-4 text-nat-clay shrink-0 mt-0.5" />
                  <span>{pairing.error || "Pairing failed. Please try again."}</span>
                </div>
                <button
                  onClick={openPair}
                  className="px-4 py-2 bg-nat-forest text-nat-bg rounded-xl text-xs font-serif font-bold inline-flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Try Again
                </button>
              </div>
            )}
          </div>

          {hb && (
            <div className="bg-nat-sage/40 border border-nat-border rounded-xl p-3 text-left text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-nat-muted">Server Status</span>
                <span className={`flex items-center gap-1 font-semibold ${hb.paired ? "text-emerald-700" : "text-nat-muted"}`}>
                  {hb.paired ? <CheckCircle2 className="w-3.5 h-3.5" /> : <span className="w-2 h-2 rounded-full bg-nat-muted" />}
                  {hb.paired ? "Online" : "Not paired"}
                </span>
              </div>
              {hb.model_ready && <div className="flex items-center justify-between"><span className="text-nat-muted">Model</span><span className="text-nat-forest font-medium">Ready</span></div>}
            </div>
          )}

          <button onClick={() => setPairOpen(false)} className="w-full py-2.5 bg-nat-forest text-nat-bg font-serif font-bold text-xs rounded-xl">Done</button>
        </div>
      </Modal>
    </div>
  )
}