import React, { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ChevronLeft, Star, MapPin, Calendar } from "lucide-react"
import { data } from "../lib/data.js"
import { CategoryBadge } from "../lib/icons.js"

export default function CardDetail() {
  const { publicId } = useParams()
  const navigate = useNavigate()
  const [card, setCard] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    data.card(publicId)
      .then((res) => {
        if (!alive) return
        if (res.card) setCard(res.card)
        else setNotFound(true)
      })
      .catch(() => alive && setNotFound(true))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publicId])

  if (loading) return <div className="flex-1 p-4 pb-24"><div className="h-72 bg-nat-sage/40 rounded-2xl animate-pulse" /></div>

  if (notFound || !card) {
    return (
      <div className="flex-1 p-4 pb-24 flex flex-col items-center justify-center text-center space-y-4">
        <p className="font-serif text-xl font-bold text-nat-forest">Card not found</p>
        <p className="text-sm text-nat-muted">You don't have access to this specimen record.</p>
        <button onClick={() => navigate("/collection")} className="px-5 py-2.5 bg-nat-forest text-nat-bg rounded-xl text-sm font-semibold">Back to Collection</button>
      </div>
    )
  }

  const sp = card.species
  const img = card.image_url || (data.isDemo() ? sp.photoUrl : null)

  return (
    <div className="flex-1 p-4 space-y-4 pb-24 animate-fade-in">
      <header className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-xs font-semibold text-nat-muted hover:text-nat-forest">
          <ChevronLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-xs font-serif font-bold text-nat-clay uppercase tracking-wider">Specimen Record</span>
        <span className="w-8" />
      </header>

      <div className="bg-nat-paper border border-nat-border rounded-2xl overflow-hidden shadow-paper p-3 space-y-3">
        <div className="relative h-64 rounded-xl overflow-hidden border border-nat-border/60 bg-nat-sage/50">
          {img ? (
            <img src={img} alt={sp.common_name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-nat-muted"><Star className="w-10 h-10" /></div>
          )}
          <div className="absolute top-3 left-3 bg-nat-bg/90 backdrop-blur-md border border-nat-border px-3 py-1 rounded-full flex items-center gap-1.5 text-xs font-semibold text-nat-forest">
            <Star className="w-3.5 h-3.5 fill-nat-golden text-nat-golden" /> {sp.rarity || "Common"} Specimen
          </div>
          <div className="absolute top-3 right-3 bg-nat-forest text-nat-bg px-3 py-1 rounded-full text-xs font-serif font-bold">×{card.count}</div>
        </div>

        <div className="space-y-1">
          <CategoryBadge category={sp.category} />
          <h1 className="font-serif text-2xl font-bold text-nat-forest leading-tight">{sp.common_name}</h1>
          <p className="font-serif italic text-sm text-nat-muted">{sp.scientific_name}</p>
        </div>

        {sp.description && <p className="text-sm text-nat-text leading-relaxed border-t border-nat-border/60 pt-3">{sp.description}</p>}

        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-nat-border/60 text-xs">
          <div className="flex items-center gap-2 text-nat-muted"><Calendar className="w-3.5 h-3.5 text-nat-clay" /> First seen: {card.first_discovered_at ? new Date(card.first_discovered_at).toLocaleDateString() : "Today"}</div>
          <div className="flex items-center gap-2 text-nat-muted"><MapPin className="w-3.5 h-3.5 text-nat-clay" /> Pine Ridge Woods</div>
        </div>
      </div>

      <button onClick={() => navigate("/discover")} className="w-full py-3 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md">
        Log another observation
      </button>
    </div>
  )
}