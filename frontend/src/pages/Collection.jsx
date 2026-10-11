import React, { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Search, Lock } from "lucide-react"
import { data } from "../lib/data.js"
import { CategoryBadge } from "../lib/icons.jsx"

const FILTERS = [
  { key: "", label: "All" },
  { key: "flora", label: "Flora" },
  { key: "fungi", label: "Fungi" },
  { key: "fauna", label: "Fauna" },
]

export default function Collection() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const active = params.get("category") || ""
  const [cards, setCards] = useState([])
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    data.collection(active || undefined)
      .then((c) => alive && setCards(Array.isArray(c) ? c : []))
      .catch(() => alive && setCards([]))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [active])

  const discovered = cards.filter((c) => c.discovered)
  const q = query.trim().toLowerCase()
  const filtered = cards.filter((c) => {
    const name = (c.species?.common_name || c.commonName || "").toLowerCase()
    const sci = (c.species?.scientific_name || c.scientificName || "").toLowerCase()
    return !q || name.includes(q) || sci.includes(q)
  })

  return (
    <div className="flex-1 p-4 space-y-4 pb-24 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-2xl font-bold text-nat-forest">Collection</h2>
          <p className="text-xs text-nat-muted">Botanical & Field Specimens</p>
        </div>
        <span className="font-serif font-bold text-sm text-nat-clay">{discovered.length} / {cards.length} Logged</span>
      </div>

      <div className="space-y-2.5">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-nat-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search species name or tag..."
            className="w-full pl-9 pr-4 py-2.5 bg-nat-paper border border-nat-border rounded-xl text-xs text-nat-text focus:outline-none focus:ring-1 focus:ring-nat-forest shadow-inner-paper"
          />
        </div>
        <div className="flex gap-1.5 overflow-x-auto pb-1 text-xs">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => { if (f.key) setParams({ category: f.key }); else setParams({}) }}
              className={`px-3 py-1.5 rounded-full font-medium whitespace-nowrap transition-colors ${active === f.key ? "bg-nat-forest text-nat-bg shadow-sm" : "bg-nat-paper border border-nat-border text-nat-muted hover:bg-nat-sage"}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-3 pt-1">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-40 bg-nat-sage/40 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 pt-1">
          {filtered.map((c) => {
            const sp = c.species || c
            if (!c.discovered) {
              return (
                <div key={sp.id} className="rounded-2xl border border-dashed border-nat-border bg-nat-paper/40 p-3 flex flex-col items-center justify-center text-center min-h-40 space-y-1.5">
                  <Lock className="w-5 h-5 text-nat-muted" />
                  <span className="font-serif font-bold text-nat-forest text-sm">???</span>
                  <CategoryBadge category={sp.category} />
                  {sp.hint && <p className="text-[11px] text-nat-muted leading-snug italic">“{sp.hint}”</p>}
                </div>
              )
            }
            return (
              <button key={c.public_id || sp.id} onClick={() => navigate(c.public_id ? `/collection/card-${c.public_id}` : "/collection")} className="text-left bg-nat-paper border border-nat-border rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-lg transition-all group">
                <div className="h-28 bg-nat-sage/50 overflow-hidden">
                  <img src={(c.image_url || sp.photoUrl)} alt={sp.common_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                </div>
                <div className="p-2.5 space-y-1">
                  <p className="font-serif font-bold text-sm text-nat-forest leading-tight truncate">{sp.common_name}</p>
                  <p className="text-[10px] text-nat-muted font-serif italic truncate">{sp.scientific_name}</p>
                  <div className="flex items-center justify-between">
                    <CategoryBadge category={sp.category} />
                    <span className="text-[10px] font-semibold text-nat-clay">{c.count ?? 1} seen</span>
                  </div>
                </div>
              </button>
            )
          })}
          {filtered.length === 0 && <p className="col-span-2 text-sm text-nat-muted text-center py-10">No specimens match your search.</p>}
        </div>
      )}
    </div>
  )
}