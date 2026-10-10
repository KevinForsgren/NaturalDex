import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Plus } from "lucide-react"
import { data } from "../lib/data.js"

export default function Journal() {
  const navigate = useNavigate()
  const [cards, setCards] = useState([])

  useEffect(() => {
    let alive = true
    data.collection()
      .then((c) => alive && setCards(Array.isArray(c) ? c.filter((x) => x.discovered) : []))
      .catch(() => {})
    return () => { alive = false }
  }, [])

  return (
    <div className="flex-1 p-4 space-y-4 pb-24 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-2xl font-bold text-nat-forest">Field Journal</h2>
          <p className="text-xs text-nat-muted">Observation Timeline & Personal Logs</p>
        </div>
        <button onClick={() => navigate("/discover")} className="p-2 rounded-xl bg-nat-forest text-nat-bg text-xs font-serif font-bold flex items-center gap-1 shadow-sm">
          <Plus className="w-4 h-4" /> Log Entry
        </button>
      </div>

      <div className="space-y-3 relative">
        {cards.length === 0 && <p className="text-sm text-nat-muted">No field entries yet. Capture your first discovery!</p>}
        {cards.map((c) => {
          const sp = c.species || c
          return (
            <button key={c.public_id || sp.id} onClick={() => navigate(c.public_id ? `/collection/card-${c.public_id}` : "/collection")} className="w-full bg-nat-paper border border-nat-border p-3 rounded-xl space-y-2 text-left hover:bg-nat-sage/30 transition-all shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-semibold text-nat-clay uppercase">
                    {c.first_discovered_at ? new Date(c.first_discovered_at).toLocaleDateString() : "Today"} • Pine Ridge Woods
                  </span>
                  <h4 className="font-serif font-bold text-sm text-nat-forest">{sp.common_name} Observation</h4>
                </div>
                <span className="text-xs font-serif text-nat-muted italic">{sp.scientific_name}</span>
              </div>
              <div className="flex gap-3">
                <div className="w-16 h-16 rounded-lg bg-nat-sage/50 overflow-hidden shrink-0">
                  {(c.image_url || sp.photoUrl) && <img src={c.image_url || sp.photoUrl} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="text-xs text-nat-muted space-y-1">
                  <p className="line-clamp-2 italic text-nat-text">“{sp.notes || sp.description || "Recorded in outdoor notebook."}”</p>
                  <span className="inline-block px-2 py-0.5 bg-nat-sage/60 rounded text-[10px] text-nat-forest font-medium">+{sp.xpValue ?? 40} XP Earned</span>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}