import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from '../../hooks/useTheme'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import {
  Search,
  LayoutDashboard,
  Mic,
  History,
  Sparkles,
  User,
  Moon,
  Globe,
  Coins,
  LogOut,
  X,
  Command,
} from 'lucide-react'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface CommandItem {
  id: string
  title: string
  category: string
  icon: any
  action: () => void
  keywords?: string
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { toggleTheme } = useTheme()
  const { logout } = useAuth()
  const toast = useToast()

  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input khi mở
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Danh sách các lệnh và trang
  const commands: CommandItem[] = [
    // Điều hướng
    {
      id: 'nav-dashboard',
      title: t('nav.dashboard') || 'Bảng điều khiển',
      category: 'Điều hướng',
      icon: LayoutDashboard,
      action: () => navigate('/'),
      keywords: 'home trang chu dashboard',
    },
    {
      id: 'nav-studio',
      title: t('nav.textToSpeech') || 'Studio Text to Speech',
      category: 'Điều hướng',
      icon: Mic,
      action: () => navigate('/studio'),
      keywords: 'tts studio tao giong doc voice',
    },
    {
      id: 'nav-history',
      title: t('nav.processHistory') || 'Lịch sử xử lý',
      category: 'Điều hướng',
      icon: History,
      action: () => navigate('/history'),
      keywords: 'history lich su audio',
    },
    {
      id: 'nav-pricing',
      title: t('nav.upgradePlan') || 'Nâng cấp gói',
      category: 'Điều hướng',
      icon: Sparkles,
      action: () => navigate('/pricing'),
      keywords: 'pricing goi cuoc nap credit',
    },
    {
      id: 'nav-credits',
      title: 'Lịch sử biến động Credit',
      category: 'Điều hướng',
      icon: Coins,
      action: () => navigate('/credits'),
      keywords: 'credits lich su giao dich so cai ledger balance',
    },
    {
      id: 'nav-profile',
      title: t('common.profile') || 'Hồ sơ người dùng',
      category: 'Điều hướng',
      icon: User,
      action: () => navigate('/profile'),
      keywords: 'profile tai khoan user',
    },

    // Hành động nhanh
    {
      id: 'act-new-tts',
      title: 'Tạo giọng nói mới',
      category: 'Hành động nhanh',
      icon: Mic,
      action: () => {
        navigate('/studio')
        toast.info('Đã mở trang Studio tạo giọng')
      },
      keywords: 'create tts audio moi',
    },
    {
      id: 'act-topup',
      title: 'Nạp thêm credit',
      category: 'Hành động nhanh',
      icon: Coins,
      action: () => navigate('/pricing'),
      keywords: 'nap credit coin payment',
    },
    {
      id: 'act-theme',
      title: 'Chuyển đổi giao diện Sáng / Tối',
      category: 'Cài đặt hệ thống',
      icon: Moon,
      action: () => {
        toggleTheme()
        toast.info('Đã chuyển đổi chủ đề giao diện')
      },
      keywords: 'theme dark light toi sang giao dien',
    },
    {
      id: 'act-lang',
      title: 'Đổi ngôn ngữ (VI ↔ EN)',
      category: 'Cài đặt hệ thống',
      icon: Globe,
      action: () => {
        const next = i18n.language.startsWith('vi') ? 'en' : 'vi'
        i18n.changeLanguage(next)
        localStorage.setItem('voxify_lang', next)
        toast.info(next === 'vi' ? 'Tiếng Việt' : 'English')
      },
      keywords: 'language ngon ngu tieng viet english',
    },
    {
      id: 'act-logout',
      title: 'Đăng xuất tài khoản',
      category: 'Tài khoản',
      icon: LogOut,
      action: async () => {
        await logout()
        navigate('/login')
      },
      keywords: 'logout dang xuat thoat',
    },
  ]

  // Lọc theo từ khóa tìm kiếm
  const filtered = commands.filter((cmd) => {
    if (!query.trim()) return true
    const q = query.toLowerCase()
    return (
      cmd.title.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q) ||
      (cmd.keywords && cmd.keywords.toLowerCase().includes(q))
    )
  })

  // Keyboard navigation trong palette
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!isOpen) return
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : 0))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filtered.length - 1))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action()
          onClose()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filtered, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Palette Container */}
      <div className="relative w-full max-w-lg rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.1] shadow-2xl overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-150">
        {/* Input bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200 dark:border-white/[0.08]">
          <Search className="w-5 h-5 text-slate-400 dark:text-white/40 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder="Tìm trang, công cụ hoặc gõ lệnh... (↑ ↓ Enter)"
            className="w-full bg-transparent text-sm text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none"
          />
          <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500 dark:text-white/40 bg-slate-100 dark:bg-white/5 px-1.5 py-0.5 rounded border border-slate-200 dark:border-white/5">
            <Command className="w-3 h-3" />
            <span>K</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:text-white/40 dark:hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results list */}
        <div className="max-h-80 overflow-y-auto p-2 scrollbar-thin">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400 dark:text-white/40">
              Không tìm thấy lệnh hoặc trang phù hợp.
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon
              const isSelected = idx === selectedIndex
              return (
                <div
                  key={cmd.id}
                  onClick={() => {
                    cmd.action()
                    onClose()
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-control cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-white border border-indigo-200 dark:border-indigo-500/30 font-semibold'
                      : 'text-slate-700 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-1.5 rounded-lg ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow-xs'
                          : 'bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-white/50'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-xs">{cmd.title}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 dark:text-white/30 font-medium">
                    {cmd.category}
                  </span>
                </div>
              )
            })
          )}
        </div>

        {/* Footer shortcuts hint */}
        <div className="px-4 py-2 border-t border-slate-200 dark:border-white/[0.06] bg-slate-50 dark:bg-[#0B0D12]/40 flex items-center justify-between text-[11px] text-slate-500 dark:text-white/40 font-mono">
          <span>Dùng ↑ ↓ để chọn &middot; ↵ thực hiện</span>
          <span>ESC để thoát</span>
        </div>
      </div>
    </div>
  )
}
