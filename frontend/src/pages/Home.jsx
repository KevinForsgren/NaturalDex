import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Compass, Laptop, Camera, Leaf } from "lucide-react"
import { data } from "../lib/data.js"
import { useToast } from "../components/Toast.jsx"
import { taskIcon } from "../lib/icons.js"

export default function Home() {
  const navigate = useNavigate()
  const toast = useToast()
  const [tasks, setTasks] = useState(null)
  const [collection, setCollection] = useState([])
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    let alive = true
    data.dailyTasks().then((t) => alive && setTasks(t)).catch(() => alive && setTasks({ tasks: [] }))
    data.collection().then((c) => alive && setCollection(c && c.length ? c : [])).catch(() => {})
    data.profile().then((p) => alive && setProfile(p)).catch(() => {})
    return () => { alive = false }
  }, [])

  const recent = collection.filter((s) => s.discovered).slice(0, 2)
  const cardTarget = (s) => {
    if (s.species && s.public_id) return `/collection/card-${s.public_id}`
    if (s.public_id) return `/collection/card-${s.public_id}`
    return "/collection"
  }

  return (
    <div className="flex-1 p-4 space-y-5 animate-fade-in pb-24">
      {/* Greeting */}
      <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 shadow-paper relative overflow-hidden">
        <div className="absolute -right-6 -bottom-6 w-28 h-28 opacity-10 pointer-events-none text-nat-forest"><Leaf className="w-full h-full" /></div>
        <div className="relative z-10 flex items-start justify-between">
          <div>
            <span className="text-xs font-semibold text-nat-clay uppercase tracking-wider">Naturalist Notebook</span>
            <h2 className="font-serif text-2xl font-bold text-nat-forest mt-0.5">Hello, Scout</h2>
          </div>
          <span className="px-2.5 py-1 bg-nat-forest/10 border border-nat-forest/20 text-nat-forest font-serif font-bold text-xs rounded-full">
            {data.isDemo() ? "Demo" : "Explorer"}
          </span>
        </div>
        {profile && (
          <div className="relative z-10 mt-4">
            <div className="flex justify-between text-xs text-nat-muted mb-1">
              <span>{profile.xp_total} XP</span>
              <span className="font-medium text-nat-forest">{profile.observations} observations</span>
            </div>
          </div>
        )}
      </div>

      {/* Daily tasks */}
      <div className="space-y-3 pt-1">
        <div className="flex items-center justify-between">
          <h3 className="font-serif font-bold text-lg text-nat-text">Today's Expeditions</h3>
          <span className="text-[10px] text-nat-sage/80 font-mono bg-nat-forest/10 px-2 py-0.5 rounded-full border border-nat-forest/20">3 Assigned • Refreshes Daily</span>
        </div>
        {!tasks ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => <div key={i} className="h-16 bg-nat-sage/40 rounded-xl animate-pulse" />)}
          </div>
        ) : tasks.tasks && tasks.tasks.length ? (
          <div className="space-y-2">
            {tasks.tasks.map((t) => {
              const isComplete = (t.progress_value || 0) >= t.target_value
              const pct = Math.min(100, Math.round(((t.progress_value || 0) / (t.target_value || 1)) * 100))
              const Icon = taskIcon(t.task.icon)
              return (
                <div key={t.id} className={`bg-nat-paper border rounded-xl p-2.5 flex items-center justify-between text-xs gap-2 ${isComplete ? "border-nat-golden/60 bg-nat-golden/10" : "border-nat-border"}`}>
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isComplete ? "bg-nat-golden text-nat-forest" : "bg-nat-sage text-nat-forest"}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className={`font-serif font-semibold text-nat-text truncate ${isComplete ? "line-through opacity-70" : ""}`}>{t.task.title}</p>
                      <div className="flex items-center gap-2 text-[10px] text-nat-muted mt-0.5">
                        <span>{t.progress_value || 0}/{t.target_value} completed</span>
                        <span className="text-nat-golden font-bold">+{t.task.xp_value || t.xp_value} XP</span>
                      </div>
                    </div>
                  </div>
                  {isComplete ? (
                    <span className="px-2 py-0.5 bg-nat-golden/20 text-nat-golden border border-nat-golden/40 rounded-full text-[10px] font-serif font-bold shrink-0">Done</span>
                  ) : (
                    <div className="w-12 h-1.5 bg-nat-sage/50 rounded-full overflow-hidden shrink-0">
                      <div className="h-full bg-nat-golden transition-all duration-300" style={{ width: `${pct}%` }} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-nat-muted">No expeditions assigned yet.</p>
        )}

        <button onClick={() => navigate("/discover")} className="w-full mt-1 py-3 px-4 bg-nat-bg hover:bg-white text-nat-forest font-serif font-bold text-sm rounded-xl shadow-md border border-nat-border flex items-center justify-center gap-2 active:scale-[0.99] transition-transform">
          <Camera className="w-4 h-4 text-nat-clay" /> Start Exploring & Scan
        </button>
      </div>

      {/* Recent entries */}
      <div className="space-y-3 pt-1">
        <h3 className="font-serif font-bold text-lg text-nat-text">Recent Field Entries</h3>
        {recent.length === 0 ? (
          <p className="text-sm text-nat-muted">Your discoveries will appear here.</p>
        ) : (
          <div className="space-y-2.5">
            {recent.map((s) => {
              const detail = (s.species || s)
              return (
                <button key={s.species ? s.public_id : s.id} onClick={() => navigate(cardTarget(s))} className="w-full bg-nat-paper border border-nat-border p-3 rounded-xl flex items-center justify-between text-left hover:bg-nat-sage/30 transition-all shadow-sm">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-12 rounded-lg bg-nat-sage/60 overflow-hidden shrink-0 flex items-center justify-center">
                      {(s.image_url || s.photoUrl) ? <img src={s.image_url || s.photoUrl} alt="" className="w-full h-full object-cover" /> : <Compass className="w-5 h-5 text-nat-forest" />}
                    </div>
                    <div className="min-w-0">
                      <p className="font-serif font-bold text-sm text-nat-forest truncate">{detail.common_name || detail.commonName}</p>
                      <p className="text-[11px] text-nat-muted font-serif italic truncate">{detail.scientific_name || detail.scientificName}</p>
                      <span className="text-[10px] text-nat-clay font-medium">{s.discoveryDate || s.first_discovered_at || "Today"} • {String(s.count ?? 1)} seen</span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}