"use client"

import * as React from "react"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"

const Toaster = () => {
  const { toasts, dismiss } = useToast()
  const timerRefs = React.useRef<{ [key: string]: NodeJS.Timeout }>({})

  React.useEffect(() => {
    if (toasts && toasts.length > 0) {
      toasts.forEach((toast) => {
        // Only set timer if one doesn't already exist for this toast
        if (toast.duration && toast.duration > 0 && !timerRefs.current[toast.id]) {
          timerRefs.current[toast.id] = setTimeout(() => {
            dismiss(toast.id)
            delete timerRefs.current[toast.id]
          }, toast.duration)
        }
      })
    }

    // Cleanup timers for removed toasts
    Object.keys(timerRefs.current).forEach((id) => {
      const toastExists = toasts?.some(t => t.id === id)
      if (!toastExists) {
        clearTimeout(timerRefs.current[id])
        delete timerRefs.current[id]
      }
    })
  }, [toasts, dismiss])

  // Cleanup all timers on unmount
  React.useEffect(() => {
    return () => {
      Object.values(timerRefs.current).forEach(timer => clearTimeout(timer))
    }
  }, [])

  if (!toasts || toasts.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "rounded-lg p-4 shadow-lg border max-w-sm relative",
            {
              "bg-green-50 border-green-200 text-green-800": toast.type === "success",
              "bg-red-50 border-red-200 text-red-800": toast.type === "error",
              "bg-blue-50 border-blue-200 text-blue-800": toast.type === "info",
            }
          )}
        >
          <button
            onClick={() => {
              if (timerRefs.current[toast.id]) {
                clearTimeout(timerRefs.current[toast.id])
                delete timerRefs.current[toast.id]
              }
              dismiss(toast.id)
            }}
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close notification"
          >
            ×
          </button>
          {toast.title && (
            <div className="font-medium mb-1 pr-6">{toast.title}</div>
          )}
          {toast.description && (
            <div className="text-sm pr-6">{toast.description}</div>
          )}
        </div>
      ))}
    </div>
  )
}

export { Toaster }