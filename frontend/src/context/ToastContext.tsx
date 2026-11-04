import React, { createContext, useContext, useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: string
  type: ToastType
  message: string
}

interface ToastContextType {
  toasts: ToastItem[]
  showToast: (arg1: string, arg2?: ToastType | string) => void
  removeToast: (id: string) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  warning: (message: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback((arg1: string, arg2?: ToastType | string) => {
    let type: ToastType = 'info'
    let message = arg1

    const validTypes: ToastType[] = ['success', 'error', 'info', 'warning']
    if (validTypes.includes(arg1 as ToastType) && arg2) {
      type = arg1 as ToastType
      message = arg2
    } else if (arg2 && validTypes.includes(arg2 as ToastType)) {
      type = arg2 as ToastType
      message = arg1
    }

    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const success = useCallback((msg: string) => showToast('success', msg), [showToast])
  const error = useCallback((msg: string) => showToast('error', msg), [showToast])
  const info = useCallback((msg: string) => showToast('info', msg), [showToast])
  const warning = useCallback((msg: string) => showToast('warning', msg), [showToast])

  return (
    <ToastContext.Provider value={{ toasts, showToast, removeToast, success, error, info, warning }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
