import React, { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { QRCodeSVG } from "qrcode.react"
import { Loader2, CheckCircle2, AlertTriangle, Wifi, WifiOff, Smartphone, Monitor } from "lucide-react"
import { data } from "../lib/data.js"

export default function PairingPage() {
  const { challenge } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState("waiting") // waiting | paired | error | expired
  const [modelReady, setModelReady] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)

  useEffect(() => {
    if (!challenge) {
      setStatus("error")
      setErrorMsg("No pairing challenge provided")
      return
    }

    let mounted = true
    let pollInterval = null

    async function checkStatus() {
      try {
        const res = await fetch(`/api/home-base/pair-status?challenge=${challenge}`, {
          credentials: "include"
        })
        const data = await res.json()
        if (!mounted) return

        if (data.status === "waiting") {
          // Continue polling
        } else if (data.status === "paired") {
          setStatus("paired")
          setModelReady(data.model_ready)
          if (pollInterval) clearInterval(pollInterval)
        } else if (data.status === "error") {
          setStatus("error")
          setErrorMsg(data.message || "Pairing failed")
          if (pollInterval) clearInterval(pollInterval)
        }
      } catch (e) {
        // Ignore network errors during polling
      }
    }

    pollInterval = setInterval(checkStatus, 2000)
    checkStatus() // Initial check

    return () => {
      mounted = false
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [challenge])

  // Build the verification URL that the phone will scan
  const verifyUrl = `${window.location.origin}/api/home-base/verify-pairing?challenge=${challenge}`

  if (status === "error") {
    return (
      <div className="min-h-screen bg-nat-bg flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm bg-nat-paper border border-nat-border rounded-2xl p-6 shadow-paper text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-nat-clay/10 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-nat-clay" />
          </div>
          <h1 className="font-serif text-xl font-bold text-nat-forest mb-2">Pairing Failed</h1>
          <p className="text-sm text-nat-muted mb-6">{errorMsg}</p>
          <button
            onClick={() => navigate("/")}
            className="w-full py-2.5 bg-nat-forest text-nat-bg font-serif font-bold text-xs rounded-xl"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  if (status === "paired") {
    return (
      <div className="min-h-screen bg-nat-bg flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm bg-nat-paper border border-nat-border rounded-2xl p-6 shadow-paper text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="font-serif text-xl font-bold text-nat-forest mb-2">Paired Successfully!</h1>
          <div className="flex items-center justify-center gap-2 text-xs mb-4">
            <Wifi className={`w-4 h-4 ${modelReady ? "text-emerald-600" : "text-nat-clay"}`} />
            <span className={modelReady ? "text-emerald-700 font-medium" : "text-nat-clay"}>
              {modelReady ? "Local Ollama model ready" : "Ollama not responding — check laptop"}
            </span>
          </div>
          <p className="text-sm text-nat-muted mb-6">You can now use Discover to identify species locally.</p>
          <button
            onClick={() => navigate("/")}
            className="w-full py-2.5 bg-nat-forest text-nat-bg font-serif font-bold text-xs rounded-xl"
          >
            Continue to App
          </button>
        </div>
      </div>
    )
  }

  // Waiting state - show QR code
  return (
    <div className="min-h-screen bg-nat-bg flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm bg-nat-paper border border-nat-border rounded-2xl p-6 shadow-paper text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="w-10 h-10 rounded-xl bg-nat-forest flex items-center justify-center text-nat-bg shadow-sm">
            <Monitor className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-serif text-xl font-bold text-nat-forest">NatureDex Home Base</h1>
            <p className="text-xs text-nat-muted">Pairing Session</p>
          </div>
        </div>

        <p className="text-sm text-nat-muted mb-4">
          Waiting for phone to scan QR code...
        </p>

        <div className="bg-white p-4 rounded-xl shadow-inner-paper mb-4">
          <QRCodeSVG value={verifyUrl} size={200} fgColor="#244A35" bgColor="#FFFFFF" level="M" />
        </div>

        <div className="space-y-2 text-xs text-nat-muted mb-4">
          <p>Challenge: <span className="font-mono">{challenge.slice(0, 20)}...</span></p>
          <div className="flex items-center justify-center gap-2">
            <Smartphone className="w-3.5 h-3.5" />
            <span>Scan this QR with your NatureDex app</span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 text-xs text-nat-muted animate-pulse">
          <Loader2 className="w-4 h-4 text-nat-forest" />
          <span>Listening for pairing...</span>
        </div>
      </div>
    </div>
  )
}