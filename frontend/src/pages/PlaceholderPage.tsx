import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useToast } from '../hooks/useToast'
import { CardSkeleton } from '../components/ui/Skeleton'
import { Sparkles, ArrowLeft, Bell } from 'lucide-react'

interface PlaceholderPageProps {
  title: string
  subtitle?: string
}

export default function PlaceholderPage({ title, subtitle }: PlaceholderPageProps) {
  const { t } = useTranslation()
  const toast = useToast()

  const handleNotifyMe = () => {
    toast.success('Đã lưu tùy chọn! Chúng tôi sẽ gửi thông báo khi tính năng ra mắt.')
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-6 animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-brand-500/10 via-purple-500/5 to-transparent border border-brand-500/20 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t('common.comingSoon')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {title}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1 max-w-lg">
            {subtitle || t('placeholder.featureInDevelopmentDesc')}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleNotifyMe}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/25 transition-all"
          >
            <Bell className="w-4 h-4" />
            <span>{t('placeholder.notifyMe')}</span>
          </button>
          <Link
            to="/"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/5 text-slate-700 dark:text-white/80 text-xs font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{t('placeholder.backToDashboard')}</span>
          </Link>
        </div>
      </div>

      {/* Skeleton Mockup Grid */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-slate-400 dark:text-white/40 uppercase tracking-wider">
          Giao diện xem trước tính năng
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    </div>
  )
}
