import { useCallback, useEffect, useRef, useState } from "react"

// Web camera helper. Uses navigator.mediaDevices.getUserMedia with a preference
// for the rear/environment-facing camera. Returns a status that the UI maps to
// the prototype's permission/unavailable modals. No gallery/file access here.
export default function useCamera(facingMode = "environment") {
  const [state, setState] = useState({ status: "idle", error: null })
  const videoRef = useRef(null)
  const streamRef = useRef(null)

  const stop = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) videoRef.current.srcObject = null
  }, [])

  const request = useCallback(async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setState({ status: "unavailable", error: "CAMERA_UNAVAILABLE" })
      return "unavailable"
    }
    setState({ status: "requesting", error: null })
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode }, width: { ideal: 1280 } },
        audio: false,
      })
      stop()
      streamRef.current = stream
      setState({ status: "ready", error: null })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {})
      }
      return "ready"
    } catch (err) {
      const name = err && err.name ? err.name : ""
      const denied = name === "NotAllowedError" || name === "PermissionDeniedError"
      setState({ status: denied ? "denied" : "unavailable",
        error: denied ? "CAMERA_PERMISSION_DENIED" : "CAMERA_UNAVAILABLE" })
      return denied ? "denied" : "unavailable"
    }
  }, [facingMode, stop])

  useEffect(() => () => stop(), [stop])

  return { state, videoRef, request, stop }
}

// Grab the current video frame as a JPEG data URL. Camera-only; never from a file.
export function captureFrame(video) {
  if (!video) return null
  const canvas = document.createElement("canvas")
  canvas.width = video.videoWidth || 1280
  canvas.height = video.videoHeight || 720
  const ctx = canvas.getContext("2d")
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL("image/jpeg", 0.85)
}

// Convert a data URL back to a Blob for upload to the backend.
export function dataUrlToBlob(dataUrl) {
  const [head, data] = dataUrl.split(",")
  const mime = (head.match(/data:(.*?);/) || [])[1] || "image/jpeg"
  const b64 = atob(data)
  const bytes = new Uint8Array(b64.length)
  for (let i = 0; i < b64.length; i++) bytes[i] = b64.charCodeAt(i)
  return new Blob([bytes], { type: mime })
}