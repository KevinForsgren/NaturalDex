import React from "react"
import { X } from "lucide-react"

// Shared modal: bottom-sheet on mobile, centered on larger screens. Matches the
// prototype's styling and is used for error states, pairing, and photo preview.
export default function Modal({ open, onClose, title, children, accent }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-nat-bg w-full max-w-md max-h-[90vh] rounded-t-2xl sm:rounded-2xl border border-nat-border overflow-y-auto shadow-2xl animate-fade-in">
        {title && (
          <div className="sticky top-0 z-10 bg-nat-bg/95 backdrop-blur-md px-4 py-3 border-b border-nat-border flex items-center justify-between">
            <span className={`text-xs font-serif font-bold uppercase tracking-wider ${accent ? accent : "text-nat-clay"}`}>
              {title}
            </span>
            {onClose && (
              <button onClick={onClose} className="p-1 rounded-full hover:bg-nat-sage text-nat-muted">
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}
        {children}
      </div>
    </div>
  )
}