import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { useToast } from '../../hooks/useToast'
import Breadcrumb from './Breadcrumb'
import {
  Menu,
  Sun,
  Moon,
  Coins,
  Plus,
  User as UserIcon,
  LogOut,
  ChevronDown,
} from 'lucide-react'

interface TopbarProps {
  onOpenMobileMenu: () => void
}

export default function Topbar({ onOpenMobileMenu }: TopbarProps) {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const toast = useToast()
  const navigate = useNavigate()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('voxify_lang', lang)
    toast.info(lang === 'vi' ? 'Đã chuyển sang Tiếng Việt' : 'Switched to English')
  }

  const handleLogout = async () => {
    setDropdownOpen(false)
    await logout()
    toast.info(t('common.logout') + '...')
    navigate('/login')
  }

  // Tên viết tắt cho avatar
  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.email.slice(0, 2).toUpperCase() || 'VX'

  return (
    <header className="h-16 border-b border-slate-200 dark:border-white/5 bg-white/80 dark:bg-[#12121d]/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      {/* Left side: Hamburger on mobile + Breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded-xl text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden sm:block">
          <Breadcrumb />
        </div>
      </div>

      {/* Right side controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Language switcher (VI | EN) */}
        <div className="flex items-center bg-slate-100 dark:bg-white/5 p-0.5 rounded-full border border-slate-200 dark:border-white/10 text-xs font-semibold">
          <button
            onClick={() => changeLanguage('vi')}
            className={`px-2.5 py-1 rounded-full transition-all ${
              i18n.language.startsWith('vi')
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                : 'text-slate-500 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            VI
          </button>
          <button
            onClick={() => changeLanguage('en')}
            className={`px-2.5 py-1 rounded-full transition-all ${
              i18n.language.startsWith('en')
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                : 'text-slate-500 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            EN
          </button>
        </div>

        {/* Dark / Light Mode Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? t('common.lightMode') : t('common.darkMode')}
          className="p-2 rounded-xl text-slate-500 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Credit chip + Top Up */}
        <div className="hidden md:flex items-center gap-1.5 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-full pl-3 pr-1 py-1">
          <Coins className="w-4 h-4 text-amber-500" />
          <span className="text-xs font-semibold text-slate-700 dark:text-white/80">
            {t('common.creditsRemaining', {
              count: user?.credits ? user.credits.toLocaleString('vi-VN') : '0',
            })}
          </span>
          <Link
            to="/pricing"
            className="flex items-center gap-1 ml-1 px-2.5 py-1 rounded-full bg-slate-900 dark:bg-brand-600 hover:bg-slate-800 dark:hover:bg-brand-500 text-white text-[11px] font-semibold transition-all shadow-sm"
          >
            <Plus className="w-3 h-3" />
            <span>{t('common.topUp')}</span>
          </Link>
        </div>

        {/* Avatar Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 p-1 rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 transition-colors focus:outline-none"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-brand-500/20">
              {initials}
            </div>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform hidden sm:block ${
                dropdownOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {/* Menu popup */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-white dark:bg-[#161624] border border-slate-200 dark:border-white/10 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
              {/* User summary */}
              <div className="px-3 py-2.5 border-b border-slate-100 dark:border-white/5 mb-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                    {user?.full_name || 'Người dùng'}
                  </p>
                  {user?.role === 'admin' && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-extrabold bg-amber-500/20 text-amber-500 border border-amber-500/30">
                      ADMIN
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/40 truncate">{user?.email}</p>
                <div className="mt-2 md:hidden flex items-center justify-between text-xs text-amber-500 font-semibold bg-amber-500/10 px-2 py-1 rounded-lg">
                  <span>Credit:</span>
                  <span>{user?.credits.toLocaleString('vi-VN')}</span>
                </div>
              </div>

              {/* Links */}
              <div className="space-y-0.5">
                <Link
                  to="/profile"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                >
                  <UserIcon className="w-4 h-4 text-slate-400" />
                  <span>{t('common.profile')}</span>
                </Link>

                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>{t('common.logout')}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
