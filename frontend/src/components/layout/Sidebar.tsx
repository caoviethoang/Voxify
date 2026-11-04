import { useState, useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAppConfig } from '../../hooks/useAppConfig'
import { useAuth } from '../../hooks/useAuth'
import {
  LayoutDashboard,
  Mic,
  AudioWaveform,
  Disc,
  FileAudio,
  FolderKanban,
  History,
  Sparkles,
  Gift,
  Code2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Pin,
  X,
  Search,
  Volume2,
  Sliders,
  Scissors,
  Share2,
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  isMobile?: boolean
  onCloseMobile?: () => void
}

interface NavItemDef {
  id: string
  label: string
  path: string
  icon: any
  badge?: string
  disabled?: boolean
  category?: string
}

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  isMobile = false,
  onCloseMobile,
}: SidebarProps) {
  const { config } = useAppConfig()
  const { user } = useAuth()
  const { t, i18n } = useTranslation()
  const location = useLocation()

  // Collapsible groups
  const [voiceGroupOpen, setVoiceGroupOpen] = useState(true)
  const [toolsGroupOpen, setToolsGroupOpen] = useState(false)
  const [toolSearch, setToolSearch] = useState('')

  // Ghim công cụ yêu thích (tối đa 5 mục)
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('voxify_pinned_tools') || '["tts", "history"]')
    } catch {
      return ['tts', 'history']
    }
  })

  const togglePin = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    let next: string[]
    if (pinnedIds.includes(id)) {
      next = pinnedIds.filter((p) => p !== id)
    } else {
      if (pinnedIds.length >= 5) {
        return // Tối đa 5 mục
      }
      next = [...pinnedIds, id]
    }
    setPinnedIds(next)
    localStorage.setItem('voxify_pinned_tools', JSON.stringify(next))
  }

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('voxify_lang', lang)
  }

  const handleLinkClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile()
    }
  }

  // Danh mục công cụ âm thanh
  const audioTools: NavItemDef[] = [
    { id: 'cutter', label: 'Cắt ghép Audio', path: '/tools/cutter', icon: Scissors, disabled: true, badge: 'Sắp ra mắt' },
    { id: 'enhancer', label: 'Lọc tạp âm AI', path: '/tools/enhancer', icon: Volume2, disabled: true, badge: 'Sắp ra mắt' },
    { id: 'equalizer', label: 'Bộ cân bằng âm sắc', path: '/tools/equalizer', icon: Sliders, disabled: true, badge: 'Sắp ra mắt' },
  ]

  const filteredTools = useMemo(() => {
    if (!toolSearch.trim()) return audioTools
    return audioTools.filter((t) => t.label.toLowerCase().includes(toolSearch.toLowerCase()))
  }, [audioTools, toolSearch])

  // Map all possible pinnable items
  const allNavItems: Record<string, NavItemDef> = {
    dashboard: { id: 'dashboard', label: t('nav.dashboard') || 'Trang chủ', path: '/', icon: LayoutDashboard },
    tts: { id: 'tts', label: 'Studio (Text to Speech)', path: '/studio', icon: Mic },
    library: { id: 'library', label: 'Thư viện giọng', path: '/voices', icon: Volume2 },
    history: { id: 'history', label: t('nav.processHistory') || 'Lịch sử xử lý', path: '/history', icon: History },
    pricing: { id: 'pricing', label: t('nav.upgradePlan') || 'Gói cước', path: '/pricing', icon: Sparkles },
    affiliate: { id: 'affiliate', label: 'Giới thiệu bạn bè', path: '/affiliate', icon: Gift, badge: '25%' },
  }

  const pinnedItems = pinnedIds.map((id) => allNavItems[id]).filter(Boolean)

  const isStudio = location.pathname === '/studio' || location.pathname === '/tts' || location.pathname === '/voice/tts'

  return (
    <aside
      className={`h-full flex flex-col transition-all duration-150 ease-in-out border-r border-white/[0.08] dark:border-white/[0.08] border-slate-200 bg-[#0B0D12] dark:bg-[#0B0D12] bg-white select-none ${
        collapsed && !isMobile ? 'w-16' : 'w-[248px]'
      }`}
    >
      {/* 1. Top Logo + APP_NAME + VI | EN */}
      <div className="h-16 flex items-center justify-between px-3.5 border-b border-white/[0.08] dark:border-white/[0.08] border-slate-100 flex-shrink-0">
        <NavLink to="/" onClick={handleLinkClick} className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-control bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-600/30 flex-shrink-0">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </div>
          {(!collapsed || isMobile) && (
            <div className="flex flex-col min-w-0">
              <span className="font-extrabold text-sm tracking-tight text-white truncate">
                {config.app_name || 'Voxify'}
              </span>
              <span className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase">
                AI Studio
              </span>
            </div>
          )}
        </NavLink>

        {/* Công tắc VI | EN */}
        {(!collapsed || isMobile) && (
          <div className="flex items-center bg-[#12151C] dark:bg-[#12151C] bg-slate-100 p-0.5 rounded-control border border-white/[0.08] text-[10px] font-bold">
            <button
              onClick={() => changeLanguage('vi')}
              className={`px-1.5 py-0.5 rounded-[6px] transition-all ${
                i18n.language.startsWith('vi')
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
                  : 'text-white/40 hover:text-white'
              }`}
            >
              VI
            </button>
            <button
              onClick={() => changeLanguage('en')}
              className={`px-1.5 py-0.5 rounded-[6px] transition-all ${
                i18n.language.startsWith('en')
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
                  : 'text-white/40 hover:text-white'
              }`}
            >
              EN
            </button>
          </div>
        )}

        {isMobile && (
          <button onClick={onCloseMobile} className="p-1 rounded text-white/50 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* 2. Scrollable Navigation List */}
      <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-5 scrollbar-thin">
        {/* Mục "Ghim" (Pinned items) */}
        {pinnedItems.length > 0 && (
          <div className="space-y-1">
            {(!collapsed || isMobile) && (
              <div className="flex items-center justify-between px-2.5 pb-1 text-[10px] font-bold tracking-wider text-white/30 uppercase">
                <span className="flex items-center gap-1.5">
                  <Pin className="w-3 h-3 text-indigo-400" />
                  Đã ghim
                </span>
                <span className="text-[9px] font-mono">{pinnedItems.length}/5</span>
              </div>
            )}
            {pinnedItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path || (item.id === 'tts' && isStudio)
              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  onClick={handleLinkClick}
                  className={`flex items-center justify-between px-2.5 py-2 rounded-control text-xs font-medium transition-all group ${
                    isActive
                      ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                      : 'text-white/70 hover:text-white hover:bg-[#12151C]'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className="w-4 h-4 flex-shrink-0 text-indigo-400" />
                    {(!collapsed || isMobile) && <span className="truncate">{item.label}</span>}
                  </div>
                  {(!collapsed || isMobile) && (
                    <button
                      onClick={(e) => togglePin(item.id, e)}
                      title="Bỏ ghim"
                      className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-white transition-opacity p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </NavLink>
              )
            })}
          </div>
        )}

        {/* Nhóm "Chính" */}
        <div className="space-y-1">
          {(!collapsed || isMobile) && (
            <div className="px-2.5 pb-1 text-[10px] font-bold tracking-wider text-white/30 uppercase">
              Chính
            </div>
          )}
          <NavLink
            to="/"
            end
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-white/70 hover:text-white hover:bg-[#12151C]'
              }`
            }
          >
            <LayoutDashboard className="w-4 h-4 flex-shrink-0 text-indigo-400" />
            {(!collapsed || isMobile) && <span>Trang chủ</span>}
          </NavLink>

          <NavLink
            to="/studio"
            onClick={handleLinkClick}
            className={`flex items-center justify-between px-2.5 py-2 rounded-control text-xs font-medium transition-all group ${
              isStudio
                ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                : 'text-white/70 hover:text-white hover:bg-[#12151C]'
            }`}
          >
            <div className="flex items-center gap-2.5 truncate">
              <Mic className="w-4 h-4 flex-shrink-0 text-indigo-400" />
              {(!collapsed || isMobile) && <span>Studio (Text to Speech)</span>}
            </div>
            {(!collapsed || isMobile) && (
              <button
                onClick={(e) => togglePin('tts', e)}
                title="Ghim lên đầu"
                className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-indigo-400 transition-opacity p-0.5"
              >
                <Pin className="w-3 h-3" />
              </button>
            )}
          </NavLink>
        </div>

        {/* Nhóm "Giọng nói" (gập được) */}
        <div className="space-y-1">
          <button
            onClick={() => setVoiceGroupOpen(!voiceGroupOpen)}
            className="w-full flex items-center justify-between px-2.5 py-1.5 text-[10px] font-bold tracking-wider text-white/30 uppercase hover:text-white/60 transition-colors"
          >
            {(!collapsed || isMobile) && <span>Giọng nói</span>}
            <ChevronDown
              className={`w-3 h-3 transition-transform ${voiceGroupOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {(voiceGroupOpen || collapsed) && (
            <div className="space-y-1">
              <NavLink
                to="/voices"
                onClick={handleLinkClick}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                      : 'text-white/70 hover:text-white hover:bg-[#12151C]'
                  }`
                }
              >
                <Volume2 className="w-4 h-4 flex-shrink-0 text-indigo-400" />
                {(!collapsed || isMobile) && <span>Thư viện giọng</span>}
              </NavLink>

              <div className="flex items-center justify-between px-2.5 py-2 rounded-control text-xs text-white/30 cursor-not-allowed opacity-60">
                <div className="flex items-center gap-2.5">
                  <Disc className="w-4 h-4 flex-shrink-0" />
                  {(!collapsed || isMobile) && <span>Giọng của tôi</span>}
                </div>
                {(!collapsed || isMobile) && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                    Sắp ra mắt
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between px-2.5 py-2 rounded-control text-xs text-white/30 cursor-not-allowed opacity-60">
                <div className="flex items-center gap-2.5">
                  <FileAudio className="w-4 h-4 flex-shrink-0" />
                  {(!collapsed || isMobile) && <span>Thay đổi giọng</span>}
                </div>
                {(!collapsed || isMobile) && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                    Sắp ra mắt
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between px-2.5 py-2 rounded-control text-xs text-white/30 cursor-not-allowed opacity-60">
                <div className="flex items-center gap-2.5">
                  <AudioWaveform className="w-4 h-4 flex-shrink-0" />
                  {(!collapsed || isMobile) && <span>Speech to Text</span>}
                </div>
                {(!collapsed || isMobile) && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                    Sắp ra mắt
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Nhóm "Công cụ âm thanh" (gập được, có ô lọc nhanh) */}
        <div className="space-y-1">
          <button
            onClick={() => setToolsGroupOpen(!toolsGroupOpen)}
            className="w-full flex items-center justify-between px-2.5 py-1.5 text-[10px] font-bold tracking-wider text-white/30 uppercase hover:text-white/60 transition-colors"
          >
            {(!collapsed || isMobile) && <span>Công cụ âm thanh</span>}
            <ChevronDown
              className={`w-3 h-3 transition-transform ${toolsGroupOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {(toolsGroupOpen || collapsed) && (!collapsed || isMobile) && (
            <div className="space-y-1.5 pt-1">
              {/* Ô lọc nhanh công cụ */}
              <div className="relative px-1 mb-2">
                <Search className="w-3.5 h-3.5 text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  placeholder="Lọc công cụ..."
                  className="w-full bg-[#12151C] border border-white/[0.08] rounded-control pl-7 pr-2 py-1 text-[11px] text-white placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {filteredTools.map((t) => {
                const Icon = t.icon
                return (
                  <div
                    key={t.id}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-control text-xs text-white/30 cursor-not-allowed opacity-60"
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4" />
                      <span>{t.label}</span>
                    </div>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                      {t.badge}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Nhóm "Dự án" & Lịch sử */}
        <div className="space-y-1">
          <div className="flex items-center justify-between px-2.5 py-2 rounded-control text-xs text-white/30 cursor-not-allowed opacity-60">
            <div className="flex items-center gap-2.5">
              <FolderKanban className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || isMobile) && <span>Dự án</span>}
            </div>
            {(!collapsed || isMobile) && (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
                Sắp ra mắt
              </span>
            )}
          </div>

          <NavLink
            to="/history"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-white/70 hover:text-white hover:bg-[#12151C]'
              }`
            }
          >
            <History className="w-4 h-4 flex-shrink-0 text-indigo-400" />
            {(!collapsed || isMobile) && <span>Lịch sử xử lý</span>}
          </NavLink>
        </div>

        {/* Nhóm "Mở rộng" */}
        <div className="space-y-1">
          {(!collapsed || isMobile) && (
            <div className="px-2.5 pb-1 text-[10px] font-bold tracking-wider text-white/30 uppercase">
              Mở rộng
            </div>
          )}
          <NavLink
            to="/pricing"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-white/70 hover:text-white hover:bg-[#12151C]'
              }`
            }
          >
            <Sparkles className="w-4 h-4 flex-shrink-0 text-[#F59E0B]" />
            {(!collapsed || isMobile) && <span>Gói cước</span>}
          </NavLink>

          <NavLink
            to="/affiliate"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center justify-between px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-white/70 hover:text-white hover:bg-[#12151C]'
              }`
            }
          >
            <div className="flex items-center gap-2.5">
              <Gift className="w-4 h-4 flex-shrink-0 text-pink-400" />
              {(!collapsed || isMobile) && <span>Giới thiệu bạn bè</span>}
            </div>
            {(!collapsed || isMobile) && (
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-[#F59E0B] border border-amber-500/30">
                25%
              </span>
            )}
          </NavLink>

          <NavLink
            to="/developers"
            onClick={handleLinkClick}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-control text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-white/70 hover:text-white hover:bg-[#12151C]'
              }`
            }
          >
            <Code2 className="w-4 h-4 flex-shrink-0 text-cyan-400" />
            {(!collapsed || isMobile) && <span>API & Developers</span>}
          </NavLink>
        </div>
      </div>

      {/* 3. Bottom Section: Thẻ mời bạn bè + User card + Nút thu gọn */}
      <div className="p-2.5 border-t border-white/[0.08] dark:border-white/[0.08] border-slate-100 bg-[#0B0D12] space-y-2 flex-shrink-0">
        {/* Thẻ nhỏ "Mời bạn bè nhận credit" */}
        {(!collapsed || isMobile) && (
          <div className="p-2.5 rounded-card bg-gradient-to-br from-indigo-950/60 to-purple-950/60 border border-indigo-500/20 relative overflow-hidden">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-white flex items-center gap-1.5">
                  <Share2 className="w-3.5 h-3.5 text-[#F59E0B]" />
                  Mời bạn bè nhận credit
                </span>
                <p className="text-[10px] text-white/50 leading-tight">
                  Tặng 1.000 credit cho bạn & người được mời.
                </p>
              </div>
            </div>
            <NavLink
              to="/affiliate"
              onClick={handleLinkClick}
              className="mt-2 block w-full py-1 text-center rounded-control bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-semibold transition-colors"
            >
              Chia sẻ liên kết
            </NavLink>
          </div>
        )}

        {/* Thẻ người dùng kèm thanh dùng credit mini */}
        <div className="p-2 rounded-card bg-[#12151C] border border-white/[0.06] flex flex-col gap-1.5">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {user?.full_name ? user.full_name[0].toUpperCase() : user?.email[0].toUpperCase()}
            </div>
            {(!collapsed || isMobile) && (
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold text-white truncate">
                  {user?.full_name || 'Người dùng'}
                </p>
                <p className="text-[10px] text-white/40 truncate font-mono">{user?.email}</p>
              </div>
            )}
          </div>

          {/* Mini credit bar */}
          {(!collapsed || isMobile) && (
            <div className="space-y-1 pt-1 border-t border-white/[0.04]">
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Credit</span>
                <span className="font-mono text-[#F59E0B] font-semibold">
                  {user?.credits?.toLocaleString('vi-VN') || '0'}
                </span>
              </div>
              <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#F59E0B] rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(((user?.credits || 0) / 10000) * 100, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Nút thu gọn / mở rộng sidebar */}
        {!isMobile && (
          <button
            onClick={onToggleCollapse}
            className="w-full flex items-center justify-center py-1.5 text-xs text-white/40 hover:text-white hover:bg-[#12151C] rounded-control transition-colors"
            title={collapsed ? 'Mở rộng sidebar (B)' : 'Thu gọn sidebar (B)'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        )}
      </div>
    </aside>
  )
}
