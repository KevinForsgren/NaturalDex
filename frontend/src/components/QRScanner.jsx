import React, { useEffect, useRef, useState } from "react"

// Load jsQR from CDN for cross-browser QR decoding
let jsQR = null
let jsQRLoadPromise = null

function loadJsQR() {
  if (jsQR) return Promise.resolve(jsQR)
  if (jsQRLoadPromise) return jsQRLoadPromise
  
  jsQRLoadPromise = new Promise((resolve, reject) => {
    if (window.jsQR) {
      jsQR = window.jsQR
      resolve(jsQR)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js'
    script.onload = () => {
      jsQR = window.jsQR
      resolve(jsQR)
    }
    script.onerror = () => reject(new Error('Failed to load jsQR'))
    document.head.appendChild(script)
  })
  return jsQRLoadPromise
}

export default function QRScanner({ onResult }) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [active, setActive] = useState(false)
  const [error, setError] = useState(null)
  const scanIntervalRef = useRef(null)
  const [usingFallback, setUsingFallback] = useState(false)

  useEffect(() => {
    let mounted = true

    async function init() {
      try {
        // Try to load jsQR for cross-browser support
        await loadJsQR()
        
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" }
        })
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          if (mounted) setActive(true)
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Camera access denied")
          setActive(false)
        }
      }
    }

    init()

    return () => {
      mounted = false
      if (scanIntervalRef.current) clearInterval(scanIntervalRef.current)
      if (videoRef.current?.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(t => t.stop())
      }
    }
  }, [])

  useEffect(() => {
    if (!active || !videoRef.current || !jsQR) return

    const canvas = canvasRef.current
    const video = videoRef.current
    const ctx = canvas.getContext('2d', { willReadFrequently: true })

    const scan = () => {
      if (!active || !videoRef.current) return
      
      try {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: "dontInvert",
        })
        
        if (code && code.data) {
          onResult(code.data)
        }
      } catch (e) {
        // Detection failed, continue scanning
      }
    }

    // Scan at ~10fps
    scanIntervalRef.current = setInterval(scan, 100)

    return () => {
      if (scanIntervalRef.current) clearInterval(scanIntervalRef.current)
    }
  }, [active, onResult])

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-4 text-center">
        <div className="bg-nat-clay/10 border border-nat-clay/30 rounded-xl p-4 text-left text-xs">
          <span className="text-nat-clay">{error}</span>
        </div>
      </div>
    )
  }

  if (!active) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-nat-forest" />
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        playsInline
        muted
      />
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ display: "none" }} />
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-48 h-48 border-2 border-nat-forest rounded-lg shadow-lg" />
      </div>
    </div>
  )
}