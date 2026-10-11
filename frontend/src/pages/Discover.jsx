import React, { useState } from "react"
import { useNavigate, Navigate } from "react-router-dom"
import {
  Camera, X, ChevronLeft, Image as ImageIcon, RotateCcw, Star, MapPin,
  Calendar, Loader2, AlertTriangle, ZoomIn, CheckCircle2, BookmarkPlus, Scan,
} from "lucide-react"
import Modal from "../components/Modal.jsx"
import { useToast } from "../components/Toast.jsx"
import { data } from "../lib/data.js"
import { useAuth } from "../state/AuthContext.jsx"
import useCamera, { captureFrame, dataUrlToBlob } from "../hooks/useCamera.js"

const CATEGORIES = [
  { key: "flora", label: "Flora" },
  { key: "fungi", label: "Fungi" },
  { key: "fauna", label: "Fauna" },
]

export default function Discover() {
  const navigate = useNavigate()
  const toast = useToast()
  const { status: authStatus } = useAuth()
  const camera = useCamera("environment")

  const [step, setStep] = useState("intro") // intro | capture | review | result
  const [slots, setSlots] = useState([null, null, null]) // {order, dataUrl}
  const [activeSlot, setActiveSlot] = useState(0)
  const [category, setCategory] = useState("flora")
  const [previewOpen, setPreviewOpen] = useState(false)
  const [lightbox, setLightbox] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null) // {code, message}

  const captured = slots.filter(Boolean).length
  const cameraReady = camera.state.status === "ready"

  if (authStatus !== "authed") {
    return <Navigate to="/login" replace />
  }

  function beginCapture() {
    camera.request().then((status) => {
      setStep(status === "ready" ? "capture" : "intro")
    })
  }

  function captureCurrent() {
    const frame = captureFrame(camera.videoRef.current)
    if (!frame) return
    setSlots((prev) => {
      const next = [...prev]
      next[activeSlot] = { order: activeSlot + 1, dataUrl: frame }
      return next
    })
    setActiveSlot((prev) => {
      // advance to the next empty slot; keep current if all filled or none after
      const idx = slots.findIndex((s, i) => i > prev && !s)
      return idx === -1 ? prev : idx
    })
  }

  function selectSlot(i) {
    setActiveSlot(i)
  }

  async function submit() {
    if (slots.some((s) => !s) || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const blobs = slots.map((s) => ({
        order: s.order, dataUrl: s.dataUrl, blob: dataUrlToBlob(s.dataUrl), contentType: "image/jpeg",
      }))
      const res = await data.discover({ blobs, categoryHint: category })
      if (res.accepted) {
        setResult(res)
        setStep("result")
      } else {
        setError({ code: res.errorCode, message: res.errorMessage || "We couldn't verify these photos. Please try again with three clear views." })
      }
    } catch (e) {
      setError({ code: e.code || "REQUEST_FAILED", message: e.message || "Something went wrong. Please try again." })
    } finally {
      setSubmitting(false)
    }
  }

  function saveToJournal() {
    if (!result) return
    toast({ type: "success", title: result.isFirstDiscovery ? "New Discovery Saved!" : "Repeat Observation!", message: `${result.specimen.commonName} added to your Field Journal.` })
    navigate(result.cardUrl)
  }

  const camViewClass =
    step === "capture" && cameraReady
      ? "absolute inset-0 w-full h-full object-cover opacity-95"
      : "hidden"

  return (
    <div className="min-h-screen flex flex-col bg-black relative">
      {/* Single always-mounted camera feed (ref stays valid across steps). */}
      <video ref={camera.videoRef} autoPlay playsInline muted className={camViewClass} />

      {/* ------------------------------------------------ INTRO ---------- */}
      {step === "intro" && (
        <div className="min-h-screen bg-nat-bg flex flex-col">
          <header className="p-4 border-b border-nat-border flex items-center justify-between">
            <button onClick={() => navigate("/")} className="inline-flex items-center gap-1 text-xs font-semibold text-nat-muted hover:text-nat-forest">
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
            <span className="text-xs font-serif font-bold text-nat-clay uppercase tracking-wider">New Discovery</span>
            <span className="w-8" />
          </header>

          <div className="p-6 space-y-6">
            <div className="text-center space-y-2">
              <div className="mx-auto w-16 h-16 rounded-3xl bg-nat-forest text-nat-bg flex items-center justify-center shadow-paper-lg">
                <Camera className="w-7 h-7" />
              </div>
              <h2 className="font-serif text-2xl font-bold text-nat-forest">Capture a Specimen</h2>
              <p className="text-sm text-nat-muted leading-relaxed">
                We need camera access to capture <strong>three live views</strong> of the same subject.
                Photos are not uploaded from your gallery — capture fresh from the rear camera.
              </p>
            </div>

            <div className="bg-nat-paper border border-nat-border rounded-2xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="w-7 h-7 rounded-lg bg-nat-forest text-nat-bg flex items-center justify-center text-xs font-bold shrink-0">1</span>
                <div><p className="text-sm font-semibold text-nat-text">Wide view</p><p className="text-xs text-nat-muted">Frame the whole subject.</p></div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-7 h-7 rounded-lg bg-nat-forest text-nat-bg flex items-center justify-center text-xs font-bold shrink-0">2</span>
                <div><p className="text-sm font-semibold text-nat-text">Angle view</p><p className="text-xs text-nat-muted">Move around for a second angle.</p></div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-7 h-7 rounded-lg bg-nat-forest text-nat-bg flex items-center justify-center text-xs font-bold shrink-0">3</span>
                <div><p className="text-sm font-semibold text-nat-text">Close detail</p><p className="text-xs text-nat-muted">Move closer for a detail shot.</p></div>
              </div>
            </div>

            {camera.state.status === "denied" || camera.state.status === "unavailable" ? (
              <button onClick={beginCapture} className="w-full py-3.5 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md">
                Retry Camera Access
              </button>
            ) : (
              <button onClick={beginCapture} className="w-full py-3.5 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md flex items-center justify-center gap-2">
                <Camera className="w-5 h-5" /> Start Camera
              </button>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------ CAPTURE -------- */}
      {step === "capture" && (
        <div className="flex flex-col flex-1 min-h-screen">
          {/* reticle overlay */}
          {!cameraReady ? (
            <div className="flex-1 flex items-center justify-center text-nat-bg">
              {camera.state.status === "requesting" ? (
                <div className="flex items-center gap-2"><Loader2 className="w-5 h-5 animate-spin" /> Requesting camera…</div>
              ) : (
                <div className="text-center space-y-3 p-6">
                  <AlertTriangle className="w-8 h-8 mx-auto text-nat-golden" />
                  <p className="text-sm text-nat-sage">Cannot access the camera.</p>
                  <button onClick={beginCapture} className="px-5 py-2.5 rounded-xl bg-nat-forest text-nat-bg text-sm font-semibold">Retry</button>
                </div>
              )}
            </div>
          ) : (
            <div className="relative flex-1" style={{ minHeight: "48vh" }}>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <div className="relative w-56 h-56 border-2 border-dashed border-nat-bg/80 rounded-2xl flex items-center justify-center animate-reticle">
                  <span className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-nat-golden" />
                  <span className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-nat-golden" />
                  <span className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-nat-golden" />
                  <span className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-nat-golden" />
                  <span className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-full text-[11px] text-nat-bg border border-white/10">
                    {slots[activeSlot] ? `Replace View ${activeSlot + 1}` : `View ${activeSlot + 1} of 3`}
                  </span>
                </div>
              </div>
              {/* top controls */}
              <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-center">
                <button onClick={() => { camera.stop(); setStep("intro") }} className="p-2 rounded-full bg-black/50 text-nat-bg backdrop-blur-sm"><X className="w-5 h-5" /></button>
                <div className="px-3 py-1 rounded-full bg-black/50 text-nat-bg text-xs backdrop-blur-sm border border-white/10 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-nat-golden" /> Location not added
                </div>
                {/* gallery icon -> in-session preview panel, NOT the OS picker */}
                <button onClick={() => setPreviewOpen(true)} className="p-2 rounded-full bg-black/50 text-nat-bg backdrop-blur-sm hover:bg-black/70" title="Review captured photos">
                  <ImageIcon className="w-5 h-5" />
                </button>
              </div>

              {/* 3 slots */}
              <div className="absolute bottom-16 inset-x-0 z-20 flex justify-center gap-2">
                {[0, 1, 2].map((i) => (
                  <button
                    key={i}
                    onClick={() => selectSlot(i)}
                    className={`relative w-16 h-20 rounded-xl border overflow-hidden transition-all ${activeSlot === i ? "border-nat-golden ring-2 ring-nat-golden/40" : "border-white/30"}`}
                  >
                    {slots[i] ? (
                      <img src={slots[i].dataUrl} alt={`View ${i + 1}`} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-black/60 backdrop-blur-sm flex items-center justify-center">
                        <span className="text-[10px] text-nat-sage">V{i + 1}</span>
                      </div>
                    )}
                    {slots[i] && (
                      <span className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-nat-forest text-nat-bg flex items-center justify-center text-[9px]">✓</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* capture controls */}
          <div className={`bg-nat-bg p-5 border-t border-nat-border z-20 ${!cameraReady ? "hidden" : ""}`}>
            {slots[activeSlot] && (
              <button onClick={() => setSlots((p) => { const n = [...p]; n[activeSlot] = null; return n })} className="mb-3 mx-auto flex items-center gap-1 text-xs text-nat-clay font-semibold">
                <RotateCcw className="w-3.5 h-3.5" /> Clear View {activeSlot + 1}
              </button>
            )}
            <div className="flex items-center justify-between px-2">
              <button onClick={() => setPreviewOpen(true)} className="p-3 rounded-full bg-nat-paper border border-nat-border text-nat-forest" title="Review captured photos">
                <ImageIcon className="w-5 h-5" />
              </button>
              <button onClick={captureCurrent} className="w-16 h-16 rounded-full border-4 border-nat-forest p-1 bg-transparent hover:scale-105 active:scale-95 transition-transform">
                <div className="w-full h-full rounded-full bg-nat-forest hover:bg-nat-forest-hover" />
              </button>
              <span className="w-12 text-center">
                <button onClick={() => setStep("review")} disabled={captured < 3} className={`text-xs font-serif font-bold py-1.5 px-3 rounded-full ${captured >= 3 ? "bg-nat-forest text-nat-bg" : "bg-nat-sage text-nat-muted"}`}>
                  {captured < 3 ? `${captured}/3` : "Review"}
                </button>
              </span>
            </div>
            <p className="text-center text-[11px] text-nat-muted mt-2">Capture {Math.max(0, 3 - captured)} more view{captured === 2 ? "" : "s"} to continue</p>
          </div>
        </div>
      )}

      {/* ------------------------------------------------ REVIEW --------- */}
      {step === "review" && (
        <div className="min-h-screen bg-nat-bg flex flex-col pb-8">
          <header className="p-4 border-b border-nat-border flex items-center justify-between">
            <button onClick={() => setStep("capture")} className="inline-flex items-center gap-1 text-xs font-semibold text-nat-muted hover:text-nat-forest">
              <ChevronLeft className="w-4 h-4" /> Retake
            </button>
            <span className="text-xs font-serif font-bold text-nat-clay uppercase tracking-wider">Review Photos</span>
            <span className="w-8" />
          </header>

          <div className="p-4 space-y-4">
            <div className="grid grid-cols-3 gap-2">
              {slots.map((s, i) => (
                <button key={i} onClick={() => setLightbox(s.dataUrl)} className="relative aspect-square rounded-xl overflow-hidden border border-nat-border group">
                  {s ? <img src={s.dataUrl} alt={`View ${i + 1}`} className="w-full h-full object-cover" /> : <div className="w-full h-full bg-nat-paper" />}
                  {s && (
                    <span className="absolute inset-0 bg-black/0 group-hover:bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <ZoomIn className="w-5 h-5 text-white" />
                    </span>
                  )}
                  <span className="absolute bottom-1 left-1 text-[9px] font-semibold text-nat-bg bg-black/50 px-1.5 py-0.5 rounded">View {i + 1}</span>
                  {s && (
                    <button onClick={(e) => { e.stopPropagation(); setSlots((p) => { const n = [...p]; n[i] = null; return n }); setActiveSlot(i); setStep("capture") }} className="absolute top-1 right-1 w-6 h-6 rounded-full bg-nat-forest text-nat-bg flex items-center justify-center" title="Retake this view">
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  )}
                </button>
              ))}
            </div>

            {/* subject category (metadata hint for identification) */}
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-nat-muted uppercase tracking-wider">Subject type</span>
              <div className="flex gap-1.5">
                {CATEGORIES.map((c) => (
                  <button key={c.key} onClick={() => setCategory(c.key)} className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${category === c.key ? "bg-nat-forest text-nat-bg" : "bg-nat-paper border border-nat-border text-nat-muted"}`}>
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={submit}
              disabled={captured < 3 || submitting}
              className="w-full py-3.5 mt-2 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold rounded-xl shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Scan className="w-5 h-5" />}
              {submitting ? "Analyzing 3 Views…" : "Submit 3 Photos"}
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------ RESULT --------- */}
      {step === "result" && result && (
        <div className="min-h-screen bg-nat-bg flex flex-col pb-8 animate-fade-in">
          <header className="p-4 border-b border-nat-border flex items-center justify-between">
            <button onClick={() => { camera.stop(); setStep("intro") }} className="inline-flex items-center gap-1 text-xs font-semibold text-nat-muted hover:text-nat-forest">
              <ChevronLeft className="w-4 h-4" /> New Capture
            </button>
            <span className="flex items-center gap-1.5 text-xs font-serif font-bold text-nat-clay uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4" /> Success — Identified
            </span>
          </header>

          <div className="p-4 space-y-4">
            <div className="bg-nat-paper border border-nat-border rounded-2xl overflow-hidden shadow-paper p-3 space-y-3">
              <div className="relative h-64 rounded-xl overflow-hidden border border-nat-border/60">
                <img src={slots[0].dataUrl} alt="Captured specimen" className="w-full h-full object-cover" />
                <div className="absolute top-3 left-3 bg-nat-bg/90 backdrop-blur-md border border-nat-border px-3 py-1 rounded-full flex items-center gap-1.5 text-xs font-semibold text-nat-forest">
                  <Star className="w-3.5 h-3.5 fill-nat-golden text-nat-golden" /> {result.specimen.rarity || "Common"} Specimen
                </div>
                <div className="absolute top-3 right-3 bg-nat-forest text-nat-bg px-3 py-1 rounded-full text-xs font-serif font-bold">+{result.specimen.xp} XP</div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-nat-muted uppercase tracking-wider">Field Identification</span>
                  <span className="text-xs font-medium text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-md">{Math.round((result.specimen.confidence || 90) * 100) / 100}% Match</span>
                </div>
                <h2 className="font-serif text-2xl font-bold text-nat-forest leading-tight">{result.specimen.commonName}</h2>
                <p className="font-serif italic text-sm text-nat-muted">{result.specimen.scientificName}</p>
              </div>

              {result.specimen.summary && <p className="text-sm text-nat-text leading-relaxed border-t border-nat-border/60 pt-3">{result.specimen.summary}</p>}

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-nat-border/60 text-xs">
                <div className="flex items-center gap-2 text-nat-muted"><Calendar className="w-3.5 h-3.5 text-nat-clay" /> Captured Today</div>
                <div className="flex items-center gap-2 text-nat-muted"><MapPin className="w-3.5 h-3.5 text-nat-clay" /> Location not added</div>
              </div>
            </div>

            <button onClick={saveToJournal} className="w-full py-3.5 px-4 bg-nat-forest hover:bg-nat-forest-hover text-nat-bg font-serif font-bold text-base rounded-xl shadow-md flex items-center justify-center gap-2">
              <BookmarkPlus className="w-5 h-5" /> Save to Field Journal
            </button>
          </div>
        </div>
      )}

      {/* ---------- in-session photo preview panel (replaces gallery picker) */}
      <Modal open={previewOpen} onClose={() => setPreviewOpen(false)} title="Captured Views">
        <div className="p-4 space-y-3">
          <p className="text-xs text-nat-muted">Your three live captures. Tap a photo to inspect it, or return to the camera to retake.</p>
          {captured === 0 ? (
            <p className="text-sm text-nat-text text-center py-6">No photos captured yet. Return to the camera and capture View 1.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {slots.filter(Boolean).map((s, i) => (
                <button key={s.order} onClick={() => { setPreviewOpen(false); setLightbox(s.dataUrl) }} className="flex items-center gap-3 bg-nat-paper border border-nat-border rounded-xl p-2 text-left">
                  <img src={s.dataUrl} alt={`View ${s.order}`} className="w-16 h-16 rounded-lg object-cover border border-nat-border" />
                  <div className="flex-1">
                    <p className="text-sm font-serif font-bold text-nat-forest">View {s.order}</p>
                    <p className="text-[11px] text-nat-muted">Live capture {String(i + 1)}</p>
                  </div>
                  <ZoomIn className="w-4 h-4 text-nat-muted" />
                </button>
              ))}
            </div>
          )}
          <button onClick={() => { setPreviewOpen(false); setStep("capture") }} className="w-full py-2.5 bg-nat-sage border border-nat-border text-nat-forest hover:bg-nat-border font-serif font-semibold text-xs rounded-xl">
            Return to Camera
          </button>
        </div>
      </Modal>

      {/* ---------------------------- lightbox / full image inspect -------- */}
      <Modal open={!!lightbox} onClose={() => setLightbox(null)}>
        <div className="p-2">
          {lightbox && <img src={lightbox} alt="Specimen view" className="w-full rounded-xl" />}
        </div>
      </Modal>

      {/* ---------------------------- error modal --------------------------- */}
      <Modal open={!!error} onClose={() => setError(null)} title="We Couldn't Verify These Photos">
        <div className="p-4 space-y-4">
          <div className="flex items-start gap-3 bg-nat-paper border border-nat-border rounded-xl p-3">
            <AlertTriangle className="w-5 h-5 text-nat-clay shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-nat-text font-semibold">{error?.message || "Something went wrong. Please try again."}</p>
              {error?.code && <p className="text-[11px] text-nat-muted mt-1">Code: {error.code}</p>}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setError(null); setStep("capture") }} className="flex-1 py-2.5 bg-nat-forest text-nat-bg font-serif font-bold text-xs rounded-xl">Retake Photos</button>
            <button onClick={() => { setError(null); setStep("review") }} className="flex-1 py-2.5 bg-nat-sage border border-nat-border text-nat-forest font-serif font-bold text-xs rounded-xl">Back to Review</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}