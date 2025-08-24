"use client"

import * as React from "react"

type ToastType = "success" | "error" | "info"

export interface Toast {
  id: string
  title?: string
  description?: string
  type: ToastType
  duration?: number
}

interface ToastState {
  toasts: Toast[]
}

const toastState: ToastState = {
  toasts: [],
}

const listeners: Array<() => void> = []

let memoryState = toastState

function dispatch(action: any) {
  memoryState = reducer(memoryState, action)
  listeners.forEach((listener) => {
    listener()
  })
}

function reducer(state: ToastState, action: any): ToastState {
  switch (action.type) {
    case "ADD_TOAST":
      return {
        ...state,
        toasts: [action.toast, ...state.toasts],
      }
    case "UPDATE_TOAST":
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === action.toast.id ? { ...t, ...action.toast } : t
        ),
      }
    case "DISMISS_TOAST": {
      const { toastId } = action
      return {
        ...state,
        toasts: state.toasts.filter((t) => t.id !== toastId),
      }
    }
    case "REMOVE_TOAST":
      return {
        ...state,
        toasts: state.toasts.filter((t) => t.id !== action.toastId),
      }
    default:
      return state
  }
}

let count = 0

function genId() {
  count = (count + 1) % Number.MAX_VALUE
  return count.toString()
}

type ToasterToast = Toast & {
  id: string
}

function toast({ ...props }: Omit<ToasterToast, "id">) {
  const id = genId()

  const update = (props: ToasterToast) =>
    dispatch({
      type: "UPDATE_TOAST",
      toast: { ...props, id },
    })
  const dismiss = () => dispatch({ type: "DISMISS_TOAST", toastId: id })

  dispatch({
    type: "ADD_TOAST",
    toast: {
      ...props,
      id,
    },
  })

  return {
    id: id,
    dismiss,
    update,
  }
}

function useToast() {
  const [state, setState] = React.useState<ToastState>(memoryState)

  React.useEffect(() => {
    const listener = () => setState(memoryState)
    listeners.push(listener)
    return () => {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [])

  return {
    toasts: state?.toasts || [],
    toast,
    dismiss: (toastId?: string) => dispatch({ type: "DISMISS_TOAST", toastId }),
  }
}

export { useToast, toast }