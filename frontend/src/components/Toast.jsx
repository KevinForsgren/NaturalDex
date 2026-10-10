import React, { createContext, useCallback, useContext, useRef, useState } from "react"
import { CheckCircle2, Info, AlertTriangle, X } from "lucide-react"

const ToastCtx = createContext(() => {})

export function useToast() {
  return useContext(ToastCtx)
}

export default function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timer = useRef(null)

  const show = useCallback(({ title, message, type = "info", duration = 3200 }) => {
    setToast({ title, message, type })
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setToast(null), duration)
  }, [])

  const Icon = toast?.type === "success" ? CheckCircle2 : toast?.type === "error" ? AlertTriangle : Info

  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && (
        <div className="fixed top-14 inset-x-0 mx-auto max-w-sm px-4 z-50 pointer-events-none animate-fade-in">
          <div className="bg-nat-forest text-nat-bg px-4 py-3 rounded-xl shadow-paper-lg flex items-center gap-3 border border-nat-golden/30">
            <Icon className="w-5 h-5 text-nat-golden shrink-0" />
            <div className="text-xs">
              <p className="font-bold font-serif text-sm">{toast.title}</p>
              {toast.message && <p className="text-nat-sage/90">{toast.message}</p>}
            </div>
            <button onClick={() => setToast(null)} className="ml-auto text-nat-sage/70 hover:text-nat-sage">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </ToastCtx.Provider>
  )
}