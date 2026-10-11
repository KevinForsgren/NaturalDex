import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Plus } from "lucide-react"
import { data } from "../lib/data.js"

function fmtDate(iso) {
  if (!iso) return "Today"
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }).toUpperCase()
}

export default function Journal() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState(null)

  useEffect(() => {
    let alive = true
    data.journal()
      .then((res) => alive && setEntries((res && res.entries) || []))
      .catch(() => alive && setEntries([]))
    return () => { alive = false }
  }, [])

  if (entries === null) {
    return <div className="flex-1 p-4 pb-24 space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-24 bg-nat-sage/40 rounded-xl animate-pulse" />)}</div>
  }

  // group by day (newest first)
  const groups = []
  const byDay = new Map()
  for (const e of entries) {
    const day = (e.created_at || "").slice(0, 10) || "today"
    if (!byDay.has(day)) byDay.set(day, [])
    byDay.get(day).push(e)
  }
  for (const [day, list] of byDay.entries()) groups.push({ day, list })

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

      {entries.length === 0 ? (
        <div className="text-center py-12 space-y-2">
          <p className="font-serif text-lg font-bold text-nat-forest">No field entries yet</p>
          <p className="text-sm text-nat-muted">Your observation timeline will appear here after your first discovery.</p>
          <button onClick={() => navigate("/discover")} className="mt-2 px-5 py-2.5 bg-nat-forest text-nat-bg rounded-xl text-sm font-semibold">Make a Discovery</button>
        </div>
      ) : (
        <div className="space-y-5 relative">
          {groups.map((g) => (
            <div key={g.day} className="space-y-2.5">
              <span className="text-[10px] font-semibold text-nat-clay uppercase tracking-wider flex items-center gap-1.5">
                {fmtDate(g.list[0].created_at)}
                {g.list[0].location_label && <span>• {g.list[0].location_label.toUpperCase()}</span>}
              </span>
              {g.list.map((e) => (
                <button
                  key={e.id}
                  onClick={() => e.card_url && navigate(e.card_url)}
                  className={`w-full bg-nat-paper border border-nat-border p-3 rounded-xl space-y-2 text-left transition-all shadow-sm ${e.card_url ? "hover:bg-nat-sage/30 cursor-pointer" : "cursor-default"}`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-serif font-bold text-sm text-nat-forest">{e.title}</h4>
                      <p className="text-[11px] text-nat-muted font-serif italic">
                        {e.species ? `${e.species.scientific_name} • ${e.location_label || "Location not added"}` : (e.location_label || "Location not added")}
                      </p>
                    </div>
                    {e.xp_earned > 0 && (
                      <span className="px-2 py-0.5 bg-nat-sage/60 rounded text-[10px] text-nat-forest font-medium shrink-0">+{e.xp_earned} XP Earned</span>
                    )}
                  </div>
                  {e.body && <p className="text-xs text-nat-muted italic line-clamp-2">“{e.body}”</p>}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}