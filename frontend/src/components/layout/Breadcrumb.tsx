import { Link, useLocation } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface BreadcrumbItem {
  label: string
  path?: string
}

export default function Breadcrumb() {
  const location = useLocation()
  const { t } = useTranslation()

  // Map route paths to i18n labels
  const getBreadcrumbs = (): BreadcrumbItem[] => {
    const path = location.pathname
    if (path === '/' || path === '/dashboard') {
      return [{ label: t('nav.dashboard') }]
    }
    if (path === '/tts' || path === '/voice/tts') {
      return [
        { label: t('nav.voice'), path: '/voice/tts' },
        { label: t('nav.textToSpeech') },
      ]
    }
    if (path === '/voice/stt') {
      return [
        { label: t('nav.voice'), path: '/voice/tts' },
        { label: t('nav.speechToText') },
      ]
    }
    if (path === '/voice/clone') {
      return [
        { label: t('nav.voice'), path: '/voice/tts' },
        { label: t('nav.voiceClone') },
      ]
    }
    if (path === '/tools') {
      return [{ label: t('nav.tools') }]
    }
    if (path === '/history') {
      return [{ label: t('nav.processHistory') }]
    }
    if (path === '/pricing') {
      return [{ label: t('nav.upgradePlan') }]
    }
    if (path === '/affiliate') {
      return [{ label: t('nav.affiliate') }]
    }
    if (path === '/developers') {
      return [{ label: t('nav.apiDevelopers') }]
    }
    if (path === '/profile') {
      return [{ label: t('common.profile') }]
    }

    return [{ label: path.replace('/', '') }]
  }

  const items = getBreadcrumbs()

  return (
    <nav className="flex items-center gap-2 text-xs text-slate-500 dark:text-white/40">
      <Link
        to="/"
        className="flex items-center gap-1 hover:text-slate-800 dark:hover:text-white transition-colors"
      >
        <Home className="w-3.5 h-3.5" />
      </Link>
      {items.map((item, index) => {
        const isLast = index === items.length - 1
        return (
          <div key={index} className="flex items-center gap-2">
            <ChevronRight className="w-3 h-3 text-slate-400 dark:text-white/20" />
            {item.path && !isLast ? (
              <Link
                to={item.path}
                className="hover:text-slate-800 dark:hover:text-white transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'font-medium text-slate-900 dark:text-white/90' : ''}>
                {item.label}
              </span>
            )}
          </div>
        )
      })}
    </nav>
  )
}

