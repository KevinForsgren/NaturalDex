import React, { useEffect, useRef, useState } from "react"

export default function QRScanner({ onResult }) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [active, setActive] = useState(false)
  const [error, setError] = useState(null)
  const detectorRef = useRef(null)
  const scanIntervalRef = useRef(null)

  useEffect(() => {
    let mounted = true

    async function init() {
      try {
        // Check for BarcodeDetector API (Chrome/Edge)
        if (!("BarcodeDetector" in window)) {
          throw new Error("Barcode detection not supported in this browser. Use Chrome or Edge.")
        }

        detectorRef.current = new BarcodeDetector({ formats: ["qr_code"] })
        
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
    if (!active || !detectorRef.current || !videoRef.current) return

    const scan = async () => {
      try {
        const barcodes = await detectorRef.current.detect(videoRef.current)
        if (barcodes.length > 0 && barcodes[0].rawValue) {
          onResult(barcodes[0].rawValue)
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