import { useState } from 'react'
import { Sparkles, X, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

interface AnnouncementBarProps {
  id?: string
  message?: string
  linkText?: string
  linkUrl?: string
  defaultOpen?: boolean
}

export default function AnnouncementBar({
  id = 'promo_launch_2026',
  message = '🎉 Chào mừng đến với phiên bản Studio mới: Tặng ngay 5.000 credit cho người dùng mới!',
  linkText = 'Khám phá ngay',
  linkUrl = '/studio',
  defaultOpen = false,
}: AnnouncementBarProps) {
  const [isOpen, setIsOpen] = useState(() => {
    // Nếu người dùng đã từng đóng banner này thì không hiện lại
    const dismissed = localStorage.getItem(`announcement_${id}`)
    return dismissed !== 'true' && defaultOpen
  })

  if (!isOpen) return null

  const handleDismiss = () => {
    setIsOpen(false)
    localStorage.setItem(`announcement_${id}`, 'true')
  }

  return (
    <div className="bg-gradient-to-r from-indigo-900/90 via-purple-900/90 to-indigo-950/90 text-white text-xs py-2 px-4 border-b border-indigo-500/20 relative flex items-center justify-center gap-3 transition-all z-50">
      <div className="flex items-center gap-2 overflow-hidden">
        <Sparkles className="w-3.5 h-3.5 text-[#F59E0B] flex-shrink-0 animate-pulse" />
        <span className="truncate">{message}</span>
        {linkUrl && (
          <Link
            to={linkUrl}
            className="hidden sm:inline-flex items-center gap-1 font-semibold text-indigo-300 hover:text-white underline underline-offset-2 ml-1 transition-colors"
          >
            <span>{linkText}</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        )}
      </div>

      <button
        onClick={handleDismiss}
        className="text-white/60 hover:text-white transition-colors p-1 rounded hover:bg-white/10 ml-auto sm:ml-0"
        title="Đóng thông báo"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}
