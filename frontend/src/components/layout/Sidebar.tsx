import { useState, useMemo } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../hooks/useAuth'
import { useAppConfig } from '../../hooks/useAppConfig'
import { useAudioTools } from '../../hooks/useAudioTools'
import { ToolIcon } from '../tools/ToolIcon'
import {
  LayoutDashboard,
  Mic,
  Volume2,
  FileAudio,
  AudioWaveform,
  History,
  Scissors,
  FolderKanban,
  Sparkles,
  Gift,
  Code2,
  Pin,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Share2,
  Disc,
  Coins,
  Wrench,
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
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  disabled?: boolean
}

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  isMobile = false,
  onCloseMobile,
}: SidebarProps) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const { config } = useAppConfig()
  const location = useLocation()

  // Trạng thái gập/mở nhóm
  const [voiceGroupOpen, setVoiceGroupOpen] = useState(true)
  const [toolsGroupOpen, setToolsGroupOpen] = useState(false)
  const [toolSearch, setToolSearch] = useState('')

  // Ghim công cụ yêu thích (lưu localStorage, tối đa 5)
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('voxify_pinned_nav') || '["tts", "library"]')
    } catch {
      return ['tts', 'library']
    }
  })

  const togglePin = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    let next: string[]
    if (pinnedIds.includes(id)) {
      next = pinnedIds.filter((p) => p !== id)
    } else {
      if (pinnedIds.length >= 5) {
        return
      }
      next = [...pinnedIds, id]
    }
    setPinnedIds(next)
    localStorage.setItem('voxify_pinned_nav', JSON.stringify(next))
  }

  // Đổi ngôn ngữ
  const changeLanguage = (lng: 'vi' | 'en') => {
    i18n.changeLanguage(lng)
    localStorage.setItem('voxify_lang', lng)
  }

  const handleLinkClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile()
    }
  }

  // Danh mục công cụ âm thanh tải động từ registry
  const { data: toolsData } = useAudioTools()

  const audioTools: NavItemDef[] = useMemo(() => {
    if (!toolsData?.categories) {
      return [
        { id: 'trim', label: 'Cắt ghép Audio', path: '/tools/trim', icon: Scissors, badge: 'Miễn phí' },
        { id: 'volume_normalize', label: 'Chuẩn hóa âm lượng', path: '/tools/volume_normalize', icon: Volume2, badge: 'Miễn phí' },
        { id: 'noise_reduction', label: 'Lọc tạp âm AI', path: '/tools/noise_reduction', icon: Sparkles, badge: 'Miễn phí' },
      ]
    }
    const tools = toolsData.categories.flatMap((c) => c.tools)
    return tools.map((tool) => ({
      id: tool.id,
      label: tool.name_vi,
      path: `/tools/${tool.id}`,
      icon: (props: { className?: string }) => <ToolIcon name={tool.icon} {...props} />,
      badge: tool.cost_type === 'free' ? 'Miễn phí' : tool.heavy ? 'GPU' : `${tool.cost_credits}cr`,
    }))
  }, [toolsData])

  const filteredTools = useMemo(() => {
    if (!toolSearch.trim()) return audioTools
    return audioTools.filter((t) => t.label.toLowerCase().includes(toolSearch.toLowerCase()))
  }, [audioTools, toolSearch])

  // Map all possible pinnable items
  const allNavItems: Record<string, NavItemDef> = {
    dashboard: { id: 'dashboard', label: t('nav.dashboard') || 'Trang chủ', path: '/', icon: LayoutDashboard },
    tts: { id: 'tts', label: 'Studio (Text to Speech)', path: '/studio', icon: Mic },
    library: { id: 'library', label: 'Thư viện giọng', path: '/voices', icon: Volume2 },
    tools: { id: 'tools', label: 'Công cụ âm thanh', path: '/tools', icon: Wrench },
    history: { id: 'history', label: t('nav.processHistory') || 'Lịch sử xử lý', path: '/history', icon: History },
    credits: { id: 'credits', label: 'Lịch sử Credit', path: '/credits', icon: Coins },
    pricing: { id: 'pricing', label: t('nav.upgradePlan') || 'Gói cước', path: '/pricing', icon: Sparkles },
    affiliate: { id: 'affiliate', label: 'Giới thiệu bạn bè', path: '/affiliate', icon: Gift, badge: '25%' },
  }

  const pinnedItems = pinnedIds.map((id) => allNavItems[id]).filter(Boolean)
  const isStudio = location.pathname === '/studio' || location.pathname === '/tts' || location.pathname === '/voice/tts'
  const isCollapsedMode = collapsed && !isMobile

  return (
    <aside
      className={`h-full flex flex-col transition-all duration-150 ease-in-out border-r border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0B0D12] select-none ${
        isCollapsedMode ? 'w-16' : 'w-[248px]'
      }`}
    >
      {/* 1. Top Logo + APP_NAME + VI | EN */}
      <div className={`h-16 flex items-center border-b border-slate-200 dark:border-white/[0.08] flex-shrink-0 ${
        isCollapsedMode ? 'justify-center px-0' : 'justify-between px-3.5'
      }`}>
        <NavLink to="/" onClick={handleLinkClick} className="flex items-center gap-2.5 min-w-0" title={config.app_name || 'Voxify'}>
          <div className="w-8 h-8 rounded-control bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-600/30 flex-shrink-0">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </div>
          {!isCollapsedMode && (
            <div className="flex flex-col min-w-0">
              <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white truncate">
                {config.app_name || 'Voxify'}
              </span>
              <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-semibold tracking-wider uppercase">
                AI Studio
              </span>
            </div>
          )}
        </NavLink>

        {/* Công tắc VI | EN */}
        {!isCollapsedMode && (
          <div className="flex items-center bg-slate-100 dark:bg-[#12151C] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08] text-[10px] font-bold">
            <button
              onClick={() => changeLanguage('vi')}
              className={`px-1.5 py-0.5 rounded-[6px] transition-all ${
                i18n.language.startsWith('vi')
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                  : 'text-slate-500 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              VI
            </button>
            <button
              onClick={() => changeLanguage('en')}
              className={`px-1.5 py-0.5 rounded-[6px] transition-all ${
                i18n.language.startsWith('en')
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                  : 'text-slate-500 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              EN
            </button>
          </div>
        )}

        {isMobile && (
          <button onClick={onCloseMobile} className="p-1 rounded text-slate-400 hover:text-slate-700 dark:text-white/50 dark:hover:text-white">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* 2. Scrollable Navigation List */}
      <div className={`flex-1 overflow-y-auto py-3 space-y-5 scrollbar-thin ${isCollapsedMode ? 'px-1.5' : 'px-2.5'}`}>
        {/* Mục "Ghim" (Pinned items) */}
        {pinnedItems.length > 0 && (
          <div className="space-y-1">
            {!isCollapsedMode && (
              <div className="flex items-center justify-between px-2.5 pb-1 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase">
                <span className="flex items-center gap-1.5">
                  <Pin className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />
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
                  title={item.label}
                  className={`flex items-center rounded-control text-xs font-medium transition-all group ${
                    isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
                  } ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
                  }`}
                >
                  <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5 truncate'}`}>
                    <Icon className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
                    {!isCollapsedMode && <span className="truncate">{item.label}</span>}
                  </div>
                  {!isCollapsedMode && (
                    <button
                      onClick={(e) => togglePin(item.id, e)}
                      title="Bỏ ghim"
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-700 dark:text-white/30 dark:hover:text-white transition-opacity p-0.5"
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
          {!isCollapsedMode && (
            <div className="px-2.5 pb-1 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase">
              Chính
            </div>
          )}
          <NavLink
            to="/"
            end
            onClick={handleLinkClick}
            title="Trang chủ"
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <LayoutDashboard className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
            {!isCollapsedMode && <span>Trang chủ</span>}
          </NavLink>

          <NavLink
            to="/studio"
            onClick={handleLinkClick}
            title="Studio (Text to Speech)"
            className={`flex items-center rounded-control text-xs font-medium transition-all group ${
              isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
            } ${
              isStudio
                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
            }`}
          >
            <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5 truncate'}`}>
              <Mic className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
              {!isCollapsedMode && <span>Studio (Text to Speech)</span>}
            </div>
            {!isCollapsedMode && (
              <button
                onClick={(e) => togglePin('tts', e)}
                title="Ghim lên đầu"
                className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-indigo-600 dark:text-white/30 dark:hover:text-indigo-400 transition-opacity p-0.5"
              >
                <Pin className="w-3 h-3" />
              </button>
            )}
          </NavLink>
        </div>

        {/* Nhóm "Giọng nói" (gập được) */}
        <div className="space-y-1">
          {!isCollapsedMode && (
            <button
              onClick={() => setVoiceGroupOpen(!voiceGroupOpen)}
              className="w-full flex items-center justify-between px-2.5 py-1.5 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase hover:text-slate-700 dark:hover:text-white/60 transition-colors"
            >
              <span>Giọng nói</span>
              <ChevronDown
                className={`w-3 h-3 transition-transform ${voiceGroupOpen ? 'rotate-180' : ''}`}
              />
            </button>
          )}

          {(voiceGroupOpen || isCollapsedMode) && (
            <div className="space-y-1">
              <NavLink
                to="/voices"
                onClick={handleLinkClick}
                title="Thư viện giọng"
                className={({ isActive }) =>
                  `flex items-center rounded-control text-xs font-medium transition-all ${
                    isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
                  } ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
                  }`
                }
              >
                <Volume2 className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
                {!isCollapsedMode && <span>Thư viện giọng</span>}
              </NavLink>

              <NavLink
                to="/voices?tab=cloned"
                onClick={handleLinkClick}
                className={() =>
                  `flex items-center rounded-control text-xs font-semibold transition-all ${
                    isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
                  } ${
                    location.pathname === '/voices' && location.search.includes('tab=cloned')
                      ? 'bg-purple-50 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
                  }`
                }
              >
                <Disc className="w-4 h-4 flex-shrink-0 text-purple-500 dark:text-purple-400" />
                {!isCollapsedMode && <span>Giọng của tôi</span>}
                {!isCollapsedMode && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 ml-auto">
                    Clone
                  </span>
                )}
              </NavLink>

              <div
                title="Thay đổi giọng (Sắp ra mắt)"
                className={`flex items-center rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none ${
                  isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
                }`}
              >
                <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5'}`}>
                  <FileAudio className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-white/30" />
                  {!isCollapsedMode && <span>Thay đổi giọng</span>}
                </div>
                {!isCollapsedMode && (
                  <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                    Sắp ra mắt
                  </span>
                )}
              </div>

              <div
                title="Speech to Text (Sắp ra mắt)"
                className={`flex items-center rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none ${
                  isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
                }`}
              >
                <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5'}`}>
                  <AudioWaveform className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-white/30" />
                  {!isCollapsedMode && <span>Speech to Text</span>}
                </div>
                {!isCollapsedMode && (
                  <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                    Sắp ra mắt
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Nhóm "Công cụ âm thanh" (gập được, có ô lọc nhanh) */}
        <div className="space-y-1">
          {!isCollapsedMode && (
            <button
              onClick={() => setToolsGroupOpen(!toolsGroupOpen)}
              className="w-full flex items-center justify-between px-2.5 py-1.5 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase hover:text-slate-700 dark:hover:text-white/60 transition-colors"
            >
              <span>Công cụ âm thanh</span>
              <ChevronDown
                className={`w-3 h-3 transition-transform ${toolsGroupOpen ? 'rotate-180' : ''}`}
              />
            </button>
          )}

          {(toolsGroupOpen || isCollapsedMode) && (
            <div className="space-y-1.5 pt-1">
              {/* Ô lọc nhanh công cụ */}
              {!isCollapsedMode && (
                <div className="relative px-1 mb-2">
                  <Search className="w-3.5 h-3.5 text-slate-400 dark:text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={toolSearch}
                    onChange={(e) => setToolSearch(e.target.value)}
                    placeholder="Lọc công cụ..."
                    className="w-full bg-slate-100 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-control pl-7 pr-2 py-1 text-[11px] text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Tất cả công cụ (Hub) */}
              <NavLink
                to="/tools"
                onClick={handleLinkClick}
                end
                title="Tất cả công cụ âm thanh"
                className={({ isActive }) =>
                  `flex items-center rounded-control text-xs font-medium transition-all ${
                    isCollapsedMode ? 'justify-center py-2 px-0' : 'gap-2.5 px-2.5 py-1.5'
                  } ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
                  }`
                }
              >
                <Wrench className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
                {!isCollapsedMode && <span>Tất cả công cụ</span>}
              </NavLink>

              {filteredTools.map((t) => {
                const Icon = t.icon
                return (
                  <NavLink
                    key={t.id}
                    to={t.path}
                    onClick={handleLinkClick}
                    title={t.label}
                    className={({ isActive }) =>
                      `flex items-center rounded-control text-xs font-medium transition-all ${
                        isCollapsedMode ? 'justify-center py-2 px-0' : 'justify-between px-2.5 py-1.5'
                      } ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
                      }`
                    }
                  >
                    <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5'} min-w-0`}>
                      <Icon className="w-4 h-4 flex-shrink-0 text-slate-500 dark:text-white/50" />
                      {!isCollapsedMode && <span className="truncate">{t.label}</span>}
                    </div>
                    {!isCollapsedMode && t.badge && (
                      <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 border border-indigo-200/60 dark:bg-indigo-500/10 dark:text-indigo-400 dark:border-indigo-500/20 flex-shrink-0 ml-1">
                        {t.badge}
                      </span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          )}
        </div>

        {/* Nhóm "Dự án" & Lịch sử */}
        <div className="space-y-1">
          <div
            title="Dự án (Sắp ra mắt)"
            className={`flex items-center rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none ${
              isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
            }`}
          >
            <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5'}`}>
              <FolderKanban className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-white/30" />
              {!isCollapsedMode && <span>Dự án</span>}
            </div>
            {!isCollapsedMode && (
              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            )}
          </div>

          <NavLink
            to="/history"
            onClick={handleLinkClick}
            title={t('nav.processHistory') || 'Lịch sử xử lý'}
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <History className="w-4 h-4 flex-shrink-0 text-indigo-500 dark:text-indigo-400" />
            {!isCollapsedMode && <span>Lịch sử xử lý</span>}
          </NavLink>

          <NavLink
            to="/credits"
            onClick={handleLinkClick}
            title="Lịch sử Credit"
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <Coins className="w-4 h-4 flex-shrink-0 text-[#F59E0B]" />
            {!isCollapsedMode && <span>Lịch sử Credit</span>}
          </NavLink>
        </div>

        {/* Nhóm "Mở rộng" */}
        <div className="space-y-1">
          {!isCollapsedMode && (
            <div className="px-2.5 pb-1 text-[10px] font-bold tracking-wider text-slate-400 dark:text-white/30 uppercase">
              Mở rộng
            </div>
          )}
          <NavLink
            to="/pricing"
            onClick={handleLinkClick}
            title={t('nav.upgradePlan') || 'Gói cước'}
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <Sparkles className="w-4 h-4 flex-shrink-0 text-[#F59E0B]" />
            {!isCollapsedMode && <span>Gói cước</span>}
          </NavLink>

          <NavLink
            to="/affiliate"
            onClick={handleLinkClick}
            title="Giới thiệu bạn bè"
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <div className={`flex items-center ${isCollapsedMode ? 'justify-center' : 'gap-2.5'}`}>
              <Gift className="w-4 h-4 flex-shrink-0 text-pink-500" />
              {!isCollapsedMode && <span>Giới thiệu bạn bè</span>}
            </div>
            {!isCollapsedMode && (
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-[#F59E0B] border border-amber-500/20">
                25%
              </span>
            )}
          </NavLink>

          <NavLink
            to="/developers"
            onClick={handleLinkClick}
            title="API & Developers"
            className={({ isActive }) =>
              `flex items-center rounded-control text-xs font-medium transition-all ${
                isCollapsedMode ? 'justify-center py-2.5 px-0' : 'gap-2.5 px-2.5 py-2'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-600/20 dark:text-white dark:border-indigo-500/30 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-white/70 dark:hover:text-white dark:hover:bg-[#12151C]'
              }`
            }
          >
            <Code2 className="w-4 h-4 flex-shrink-0 text-cyan-600 dark:text-cyan-400" />
            {!isCollapsedMode && <span>API & Developers</span>}
          </NavLink>
        </div>
      </div>

      {/* 3. Bottom Section: Thẻ mời bạn bè + User card + Nút thu gọn */}
      <div className={`border-t border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#0B0D12] space-y-2 flex-shrink-0 ${
        isCollapsedMode ? 'p-1.5' : 'p-2.5'
      }`}>
        {/* Thẻ nhỏ "Mời bạn bè nhận credit" - Chỉ hiện khi mở rộng */}
        {!isCollapsedMode && (
          <div className="p-2.5 rounded-card bg-gradient-to-br from-indigo-50/80 to-purple-50/80 dark:from-indigo-950/60 dark:to-purple-950/60 border border-indigo-200/60 dark:border-indigo-500/20 relative overflow-hidden">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <Share2 className="w-3.5 h-3.5 text-[#F59E0B]" />
                  Mời bạn bè nhận credit
                </span>
                <p className="text-[10px] text-slate-600 dark:text-white/50 leading-tight">
                  Tặng 1.000 credit cho bạn & người được mời.
                </p>
              </div>
            </div>
            <NavLink
              to="/affiliate"
              onClick={handleLinkClick}
              className="mt-2 block w-full py-1 text-center rounded-control bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-semibold transition-colors shadow-xs"
            >
              Chia sẻ liên kết
            </NavLink>
          </div>
        )}

        {/* Thẻ người dùng */}
        <div className={`rounded-card bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.06] ${
          isCollapsedMode ? 'p-1.5 flex justify-center' : 'p-2 flex flex-col gap-1.5'
        }`}>
          <div className="flex items-center gap-2 min-w-0" title={user?.email}>
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {user?.full_name ? user.full_name[0].toUpperCase() : user?.email ? user.email[0].toUpperCase() : 'U'}
            </div>
            {!isCollapsedMode && (
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold text-slate-900 dark:text-white truncate">
                  {user?.full_name || 'Người dùng'}
                </p>
                <p className="text-[10px] text-slate-500 dark:text-white/40 truncate font-mono">{user?.email}</p>
              </div>
            )}
          </div>

          {/* Mini credit bar */}
          {!isCollapsedMode && (
            <Link
              to="/credits"
              onClick={handleLinkClick}
              className="space-y-1 pt-1 border-t border-slate-200/60 dark:border-white/[0.04] block hover:opacity-80 transition-opacity"
              title="Xem chi tiết sổ cái và lịch sử credit"
            >
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500 dark:text-white/40">Credit (Lịch sử)</span>
                <span className="font-mono text-[#F59E0B] font-semibold">
                  {user?.credits?.toLocaleString('vi-VN') || '0'} &rarr;
                </span>
              </div>
              <div className="h-1 w-full bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#F59E0B] rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(((user?.credits || 0) / 10000) * 100, 100)}%` }}
                />
              </div>
            </Link>
          )}
        </div>

        {/* Nút thu gọn / mở rộng sidebar */}
        {!isMobile && (
          <button
            onClick={onToggleCollapse}
            className="w-full flex items-center justify-center py-1.5 text-xs text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:text-white/40 dark:hover:text-white dark:hover:bg-[#12151C] rounded-control transition-colors"
            title={collapsed ? 'Mở rộng sidebar (B)' : 'Thu gọn sidebar (B)'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        )}
      </div>
    </aside>
  )
}
