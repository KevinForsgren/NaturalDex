import React, { useEffect, useState } from "react"
import { Laptop, ShieldCheck, CloudOff, Download, ChevronRight } from "lucide-react"
import { data } from "../lib/data.js"
import { useToast } from "../components/Toast.jsx"
import Modal from "../components/Modal.jsx"

export default function Profile() {
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [pairOpen, setPairOpen] = useState(false)

  useEffect(() => {
    let alive = true
    data.profile().then((p) => alive && setStats(p)).catch(() => {})
    return () => { alive = false }
  }, [])

  function exportJournal() {
    const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), mode: data.mode(), message: "NatureDex field journal (demo export)" }, null, 2)], { type: "application/json" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = "naturedex_field_journal.json"
    a.click()
    URL.revokeObjectURL(a.href)
    toast({ type: "success", title: "Journal Exported", message: "Downloaded naturedex_field_journal.json" })
  }

  return (
    <div className="flex-1 p-4 space-y-5 pb-24 animate-fade-in">
      {/* Naturalist ID */}
      <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 shadow-paper space-y-3 relative overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-full bg-nat-forest text-nat-bg font-serif font-bold text-xl flex items-center justify-center border-2 border-nat-golden shadow-sm">S</div>
          <div>
            <h3 className="font-serif font-bold text-lg text-nat-forest">Scout Naturalist</h3>
            <p className="text-xs text-nat-muted">Joined October 2026 • Sector 7</p>
            <span className="inline-block mt-1 px-2 py-0.5 bg-nat-sage/80 border border-nat-border rounded-md text-[10px] font-semibold text-nat-forest">Rank: Field Naturalist</span>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-nat-border/60 text-center text-xs">
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-forest">{stats?.unique_species ?? 0}</span><span className="text-nat-muted text-[11px]">Species</span></div>
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-forest">{stats?.observations ?? 0}</span><span className="text-nat-muted text-[11px]">Logs</span></div>
          <div className="p-2 bg-nat-bg/60 rounded-lg"><span className="block font-serif font-bold text-base text-nat-clay">{stats?.xp_total ?? 0}</span><span className="text-nat-muted text-[11px]">XP</span></div>
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
          <button onClick={() => setPairOpen(true)} className="w-full p-3 flex items-center justify-between text-left hover:bg-nat-sage/30">
            <div className="flex items-center gap-2.5"><Laptop className="w-4 h-4 text-nat-forest" /><div><p className="font-medium text-nat-text">Laptop-Hosted AI Model</p><p className="text-[10px] text-nat-muted">Pair your local home base</p></div></div>
            <ChevronRight className="w-4 h-4 text-nat-muted" />
          </button>
          <div className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5"><CloudOff className="w-4 h-4 text-nat-muted" /><div><p className="font-medium text-nat-text">Mode</p><p className="text-[10px] text-nat-muted">{data.isDemo() ? "Demo data (in-browser)" : "Connected to backend"}</p></div></div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${data.isDemo() ? "bg-nat-golden/20 text-nat-golden" : "bg-nat-sage text-nat-forest"}`}>{data.isDemo() ? "Demo" : "Live"}</span>
          </div>
        </div>
      </div>

      <button onClick={exportJournal} className="w-full py-2.5 px-4 bg-nat-sage border border-nat-border text-nat-forest hover:bg-nat-border font-serif font-semibold text-xs rounded-xl transition-all flex items-center justify-center gap-2">
        <Download className="w-4 h-4" /> Export Notebook (JSON)
      </button>

      {/* Pairing modal */}
      <Modal open={pairOpen} onClose={() => setPairOpen(false)} title="Home-Base AI Model" accent="text-nat-clay">
        <div className="p-5 space-y-4 text-center">
          <p className="text-xs text-nat-muted leading-relaxed">Pair NatureDex with your local laptop to run identification without the cloud.</p>
          <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 flex flex-col items-center gap-3">
            <div className="w-40 h-40 bg-white rounded-lg flex items-center justify-center text-nat-muted">
              <Laptop className="w-16 h-16" />
            </div>
            <p className="text-xs text-nat-muted">{data.isDemo() ? "Demo: pairing QR simulated." : "Scan with the laptop home-base to redeem a single-use code."}</p>
            <button onClick={() => { setPairOpen(false); toast({ title: "Edge AI Paired", message: "Home base ready for inference." }) }} className="px-4 py-2 bg-nat-forest text-nat-bg rounded-xl text-xs font-serif font-bold">Simulate Pair</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}