"use client"

import * as React from "react"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"

const Toaster = () => {
  const { toasts } = useToast()

  React.useEffect(() => {
    if (toasts && toasts.length > 0) {
      toasts.forEach((toast) => {
        if (toast.duration && toast.duration > 0) {
          setTimeout(() => {
            // Auto dismiss after duration
          }, toast.duration)
        }
      })
    }
  }, [toasts])

  if (!toasts || toasts.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "rounded-lg p-4 shadow-lg border max-w-sm",
            {
              "bg-green-50 border-green-200 text-green-800": toast.type === "success",
              "bg-red-50 border-red-200 text-red-800": toast.type === "error",
              "bg-blue-50 border-blue-200 text-blue-800": toast.type === "info",
            }
          )}
        >
          {toast.title && (
            <div className="font-medium mb-1">{toast.title}</div>
          )}
          {toast.description && (
            <div className="text-sm">{toast.description}</div>
          )}
        </div>
      ))}
    </div>
  )
}

export { Toaster }