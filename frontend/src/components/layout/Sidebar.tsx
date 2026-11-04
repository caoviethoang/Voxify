import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Mic,
  AudioWaveform,
  Disc,
  Languages,
  Video,
  Wrench,
  History,
  Sparkles,
  Gift,
  Code2,
  Handshake,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  isMobile?: boolean
  onCloseMobile?: () => void
}

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  isMobile = false,
  onCloseMobile,
}: SidebarProps) {
  const { t } = useTranslation()
  const location = useLocation()

  // Mở rộng submenu Voice khi đang ở route con của voice
  const isVoiceRoute = location.pathname.startsWith('/voice') || location.pathname === '/tts'
  const [voiceOpen, setVoiceOpen] = useState(true)

  const handleLinkClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile()
    }
  }

  return (
    <aside
      className={`h-full flex flex-col transition-all duration-300 ease-in-out border-r border-slate-200 dark:border-white/5 bg-white dark:bg-[#12121d] select-none ${
        collapsed && !isMobile ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-100 dark:border-white/5">
        <NavLink
          to="/"
          onClick={handleLinkClick}
          className="flex items-center gap-3 overflow-hidden"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/20 flex-shrink-0">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </div>
          {(!collapsed || isMobile) && (
            <div className="flex flex-col">
              <span className="font-extrabold text-lg tracking-tight text-slate-900 dark:text-white">
                {t('common.appName')}
              </span>
              <span className="text-[10px] text-brand-600 dark:text-brand-400 font-semibold uppercase tracking-wider">
                Studio
              </span>
            </div>
          )}
        </NavLink>

        {isMobile ? (
          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-white/60 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        ) : (
          <button
            onClick={onToggleCollapse}
            title={collapsed ? 'Mở rộng menu' : 'Thu gọn menu'}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Navigation Scrollable Area */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin">
        {/* Main Section */}
        <div className="space-y-1">
          {/* Bảng điều khiển */}
          <NavLink
            to="/"
            end
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
            {(!collapsed || isMobile) && <span>{t('nav.dashboard')}</span>}
          </NavLink>

          {/* Voice Group */}
          <div className="space-y-1">
            <button
              onClick={() => setVoiceOpen(!voiceOpen)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isVoiceRoute
                  ? 'text-slate-900 dark:text-white font-semibold'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-3">
                <Mic className="w-4 h-4 flex-shrink-0 text-brand-500" />
                {(!collapsed || isMobile) && <span>{t('nav.voice')}</span>}
              </div>
              {(!collapsed || isMobile) && (
                <ChevronDown
                  className={`w-3.5 h-3.5 text-slate-400 transition-transform ${
                    voiceOpen ? 'rotate-180' : ''
                  }`}
                />
              )}
            </button>

            {/* Voice Subitems */}
            {(voiceOpen || collapsed) && (!collapsed || isMobile) && (
              <div className="pl-4 pr-1 space-y-1">
                {/* Text to Speech */}
                <NavLink
                  to="/voice/tts"
                  onClick={handleLinkClick}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive || location.pathname === '/tts'
                        ? 'bg-brand-500/10 text-brand-600 dark:bg-brand-500/20 dark:text-brand-400 border border-brand-500/20'
                        : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
                    }`
                  }
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                  <span>{t('nav.textToSpeech')}</span>
                </NavLink>

                {/* Speech to Text (disabled) */}
                <div
                  className="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-slate-400 dark:text-white/30 cursor-not-allowed opacity-75"
                  title={t('common.comingSoon')}
                >
                  <div className="flex items-center gap-2">
                    <AudioWaveform className="w-3.5 h-3.5" />
                    <span>{t('nav.speechToText')}</span>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/20 font-medium">
                    {t('common.comingSoon')}
                  </span>
                </div>

                {/* Voice Clone (disabled) */}
                <div
                  className="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-slate-400 dark:text-white/30 cursor-not-allowed opacity-75"
                  title={t('common.comingSoon')}
                >
                  <div className="flex items-center gap-2">
                    <Disc className="w-3.5 h-3.5" />
                    <span>{t('nav.voiceClone')}</span>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/20 font-medium">
                    {t('common.comingSoon')}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Dịch (disabled) */}
          <div
            className="flex items-center justify-between px-3 py-2.5 rounded-xl text-xs text-slate-400 dark:text-white/30 cursor-not-allowed opacity-75"
            title={t('common.comingSoon')}
          >
            <div className="flex items-center gap-3">
              <Languages className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || isMobile) && <span>{t('nav.translation')}</span>}
            </div>
            {(!collapsed || isMobile) && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-white/40">
                {t('common.comingSoon')}
              </span>
            )}
          </div>

          {/* Video (disabled) */}
          <div
            className="flex items-center justify-between px-3 py-2.5 rounded-xl text-xs text-slate-400 dark:text-white/30 cursor-not-allowed opacity-75"
            title={t('common.comingSoon')}
          >
            <div className="flex items-center gap-3">
              <Video className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || isMobile) && <span>{t('nav.video')}</span>}
            </div>
            {(!collapsed || isMobile) && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-white/40">
                {t('common.comingSoon')}
              </span>
            )}
          </div>

          {/* Công cụ */}
          <NavLink
            to="/tools"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <div className="flex items-center gap-3">
              <Wrench className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || isMobile) && <span>{t('nav.tools')}</span>}
            </div>
          </NavLink>

          {/* Lịch sử xử lý */}
          <NavLink
            to="/history"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <History className="w-4 h-4 flex-shrink-0" />
            {(!collapsed || isMobile) && <span>{t('nav.processHistory')}</span>}
          </NavLink>
        </div>

        {/* MỞ RỘNG (EXPAND) */}
        <div className="space-y-1">
          {(!collapsed || isMobile) && (
            <div className="px-3 pb-1 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase">
              {t('nav.extended')}
            </div>
          )}

          {/* Nâng cấp gói */}
          <NavLink
            to="/pricing"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <Sparkles className="w-4 h-4 flex-shrink-0 text-amber-500" />
            {(!collapsed || isMobile) && <span>{t('nav.upgradePlan')}</span>}
          </NavLink>

          {/* Affiliate (25%) */}
          <NavLink
            to="/affiliate"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <div className="flex items-center gap-3">
              <Gift className="w-4 h-4 flex-shrink-0 text-rose-500" />
              {(!collapsed || isMobile) && <span>{t('nav.affiliate')}</span>}
            </div>
            {(!collapsed || isMobile) && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-500 border border-amber-500/30">
                25%
              </span>
            )}
          </NavLink>

          {/* API & Developers */}
          <NavLink
            to="/developers"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white/10 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`
            }
          >
            <Code2 className="w-4 h-4 flex-shrink-0 text-blue-500" />
            {(!collapsed || isMobile) && <span>{t('nav.apiDevelopers')}</span>}
          </NavLink>

          {/* Đối tác & Ưu đãi (disabled) */}
          <div
            className="flex items-center justify-between px-3 py-2.5 rounded-xl text-xs text-slate-400 dark:text-white/30 cursor-not-allowed opacity-75"
            title={t('common.comingSoon')}
          >
            <div className="flex items-center gap-3">
              <Handshake className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || isMobile) && <span>{t('nav.partners')}</span>}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
