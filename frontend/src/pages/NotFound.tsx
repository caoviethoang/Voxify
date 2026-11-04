import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Home, AlertCircle } from 'lucide-react'

export default function NotFound() {
  const { t } = useTranslation()

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center px-4 animate-in fade-in duration-200">
      <div className="w-16 h-16 rounded-2xl bg-brand-500/10 text-brand-500 border border-brand-500/20 flex items-center justify-center mb-6">
        <AlertCircle className="w-8 h-8" />
      </div>

      <span className="text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-purple-600">
        404
      </span>

      <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
        {t('common.pageNotFound')}
      </h1>

      <p className="text-xs sm:text-sm text-slate-500 dark:text-white/40 mt-2 max-w-sm">
        {t('common.pageNotFoundDesc')}
      </p>

      <div className="mt-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 text-xs font-semibold shadow-lg shadow-black/10 dark:shadow-white/5 transition-all"
        >
          <Home className="w-4 h-4" />
          <span>{t('common.backToHome')}</span>
        </Link>
      </div>
    </div>
  )
}

