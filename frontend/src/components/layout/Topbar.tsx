import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { useToast } from '../../hooks/useToast'
import CreditChip from '../ui/CreditChip'
import CommandPalette from '../ui/CommandPalette'
import {
  Menu,
  Sun,
  Moon,
  Bell,
  Search,
  Command,
  User as UserIcon,
  Settings,
  LogOut,
  ChevronDown,
  Edit2,
  Check,
} from 'lucide-react'

interface TopbarProps {
  onOpenMobileMenu: () => void
  onToggleSidebar?: () => void
}

export default function Topbar({ onOpenMobileMenu }: TopbarProps) {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const toast = useToast()
  const location = useLocation()
  const navigate = useNavigate()

  // Trạng thái Command Palette
  const [isCommandOpen, setIsCommandOpen] = useState(false)

  // Trạng thái Dropdown Avatar & Thông báo
  const [avatarOpen, setAvatarOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const avatarRef = useRef<HTMLDivElement>(null)
  const notifRef = useRef<HTMLDivElement>(null)

  // Kiểm tra trang hiện tại có phải Studio không
  const isStudio = location.pathname === '/studio' || location.pathname === '/tts' || location.pathname === '/voice/tts'

  // Tiêu đề dự án sửa trực tiếp trên Topbar khi ở Studio
  const [projectTitle, setProjectTitle] = useState(() => {
    return localStorage.getItem('voxify_current_project_title') || 'Dự án chưa có tiêu đề'
  })
  const [isEditingTitle, setIsEditingTitle] = useState(false)

  const handleTitleChange = (newTitle: string) => {
    setProjectTitle(newTitle)
    localStorage.setItem('voxify_current_project_title', newTitle)
  }

  // Đóng dropdowns khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarOpen(false)
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Phím tắt toàn cục ⌘K / Ctrl+K
  useEffect(() => {
    function handleGlobalKeys(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsCommandOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleGlobalKeys)
    return () => window.removeEventListener('keydown', handleGlobalKeys)
  }, [])

  const handleLogout = async () => {
    setAvatarOpen(false)
    await logout()
    toast.info('Đã đăng xuất.')
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.email.slice(0, 2).toUpperCase() || 'VX'

  return (
    <>
      <header className="h-16 border-b border-slate-200 dark:border-white/[0.08] bg-white/90 dark:bg-[#0B0D12]/90 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-3 sm:px-6">
        {/* 1. Bên trái: Hamburger mobile + Tiêu đề trang / Ô sửa tên dự án trực tiếp */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden p-2 rounded-control text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>

          {isStudio ? (
            /* Ô sửa tiêu đề dự án trực tiếp */
            <div className="flex items-center gap-2 max-w-xs sm:max-w-md min-w-0">
              {isEditingTitle ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={projectTitle}
                    onChange={(e) => handleTitleChange(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && setIsEditingTitle(false)}
                    autoFocus
                    onBlur={() => setIsEditingTitle(false)}
                    className="bg-white dark:bg-[#181C25] border border-indigo-500 rounded-control px-2.5 py-1 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none"
                  />
                  <button
                    onClick={() => setIsEditingTitle(false)}
                    className="p-1 rounded text-emerald-500 hover:text-emerald-400"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => setIsEditingTitle(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer group transition-colors min-w-0"
                  title="Bấm để đổi tên dự án"
                >
                  <span className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white truncate">
                    {projectTitle}
                  </span>
                  <Edit2 className="w-3 h-3 text-slate-400 dark:text-white/30 group-hover:text-indigo-500 transition-colors flex-shrink-0" />
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono hidden sm:inline-block ml-1 opacity-70">
                    (Đã lưu)
                  </span>
                </div>
              )}
            </div>
          ) : (
            /* Tiêu đề trang thông thường */
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white">
                {location.pathname === '/' ? 'Bảng điều khiển' : location.pathname.replace('/', '')}
              </span>
            </div>
          )}
        </div>

        {/* 2. Ở giữa: Ô tìm kiếm toàn cục + ⌘K */}
        <div className="hidden md:flex items-center flex-1 max-w-sm mx-4">
          <button
            onClick={() => setIsCommandOpen(true)}
            className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-control bg-slate-100 hover:bg-slate-200/70 dark:bg-[#12151C] dark:hover:border-white/[0.18] border border-slate-200 dark:border-white/[0.08] text-xs text-slate-600 dark:text-white/40 transition-all cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5" />
              <span>Tìm kiếm hoặc gõ lệnh...</span>
            </div>
            <div className="flex items-center gap-0.5 text-[10px] font-mono bg-white dark:bg-white/5 px-1.5 py-0.5 rounded border border-slate-200 dark:border-white/5 text-slate-600 dark:text-white/60">
              <Command className="w-2.5 h-2.5" />
              <span>K</span>
            </div>
          </button>
        </div>

        {/* 3. Bên phải: Dark/Light, Chuông thông báo, Chip Credit, Avatar */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Nút tìm kiếm icon trên mobile */}
          <button
            onClick={() => setIsCommandOpen(true)}
            className="md:hidden p-2 rounded-control text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5"
          >
            <Search className="w-4 h-4" />
          </button>

          {/* Đổi Dark / Light */}
          <button
            onClick={toggleTheme}
            title={theme === 'dark' ? t('common.lightMode') : t('common.darkMode')}
            className="p-2 rounded-control text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-[#F59E0B]" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Chuông thông báo */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setNotifOpen(!notifOpen)}
              className="p-2 rounded-control text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors relative"
              title="Thông báo"
            >
              <Bell className="w-4 h-4" />
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 absolute top-1.5 right-1.5" />
            </button>

            {notifOpen && (
              <div className="absolute right-0 mt-2 w-72 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.1] shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-white/[0.08]">
                  <span className="text-xs font-bold text-slate-900 dark:text-white">Thông báo</span>
                  <span className="text-[10px] text-indigo-600 dark:text-indigo-400 cursor-pointer font-medium">Đánh dấu đã đọc</span>
                </div>
                <div className="py-3 text-center text-xs text-slate-500 dark:text-white/40">
                  🎉 Chào mừng bạn đến với Voxify Studio 2.0!
                </div>
              </div>
            )}
          </div>

          {/* Chip credit có vòng tròn tiến độ */}
          <div className="hidden sm:block">
            <CreditChip
              credits={user?.credits ?? 0}
              onTopUpClick={() => navigate('/pricing')}
            />
          </div>

          {/* Avatar Menu */}
          <div className="relative" ref={avatarRef}>
            <button
              onClick={() => setAvatarOpen(!avatarOpen)}
              className="flex items-center gap-1.5 p-1 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 transition-colors focus:outline-none"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-indigo-600/30">
                {initials}
              </div>
              <ChevronDown
                className={`w-3.5 h-3.5 text-slate-400 transition-transform hidden sm:block ${
                  avatarOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {avatarOpen && (
              <div className="absolute right-0 mt-2 w-60 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.1] shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-white/[0.08] mb-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                      {user?.full_name || 'Người dùng'}
                    </p>
                    {user?.role === 'admin' && (
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-[#F59E0B] border border-amber-500/30">
                        ADMIN
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-white/40 truncate font-mono">{user?.email}</p>

                  <div className="mt-2 sm:hidden">
                    <CreditChip credits={user?.credits ?? 0} onTopUpClick={() => navigate('/pricing')} />
                  </div>
                </div>

                <div className="space-y-0.5">
                  <Link
                    to="/profile"
                    onClick={() => setAvatarOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-control text-xs font-medium text-slate-700 dark:text-white/70 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                  >
                    <UserIcon className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                    <span>Hồ sơ cá nhân</span>
                  </Link>

                  <Link
                    to="/profile"
                    onClick={() => setAvatarOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-control text-xs font-medium text-slate-700 dark:text-white/70 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                  >
                    <Settings className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                    <span>Cài đặt</span>
                  </Link>

                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-control text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Đăng xuất</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Command Palette Modal */}
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
    </>
  )
}
