import { FolderOpen } from 'lucide-react'

interface EmptyStateProps {
  icon?: any
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({
  icon: Icon = FolderOpen,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-8 rounded-card border border-dashed border-white/[0.08] dark:border-white/[0.08] border-slate-200 bg-[#12151C]/50 dark:bg-[#12151C]/50 bg-slate-50/50">
      <div className="w-12 h-12 rounded-card bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-bold text-slate-800 dark:text-white">{title}</h4>
      {description && (
        <p className="text-xs text-slate-400 dark:text-white/40 mt-1 max-w-sm">
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-sm transition-all"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
