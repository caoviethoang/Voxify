import { useToast } from '../../hooks/useToast'
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react'

export default function ToastContainer() {
  const { toasts, removeToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        let bgStyle = 'bg-[#1b1b2a] border-white/10 text-white'
        let Icon = Info
        let iconColor = 'text-blue-400'

        if (toast.type === 'success') {
          bgStyle = 'bg-[#12241b] border-emerald-500/30 text-white'
          Icon = CheckCircle2
          iconColor = 'text-emerald-400'
        } else if (toast.type === 'error') {
          bgStyle = 'bg-[#281519] border-red-500/30 text-white'
          Icon = AlertCircle
          iconColor = 'text-red-400'
        } else if (toast.type === 'warning') {
          bgStyle = 'bg-[#291f11] border-amber-500/30 text-white'
          Icon = AlertTriangle
          iconColor = 'text-amber-400'
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-xl backdrop-blur-md transition-all animate-in fade-in slide-in-from-bottom-2 duration-200 ${bgStyle}`}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconColor}`} />
            <div className="flex-1 text-xs font-medium leading-relaxed">{toast.message}</div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-white/40 hover:text-white transition-colors p-0.5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}

