import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Mic, Volume2, History, User } from 'lucide-react'

export default function BottomTabBar() {
  const location = useLocation()
  const isStudio = location.pathname === '/studio' || location.pathname === '/tts' || location.pathname === '/voice/tts'

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 h-14 bg-[#0B0D12]/95 dark:bg-[#0B0D12]/95 bg-white/95 border-t border-white/[0.08] dark:border-white/[0.08] border-slate-200 backdrop-blur-lg flex items-center justify-around px-2 z-40 select-none">
      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
            isActive ? 'text-indigo-400 font-semibold' : 'text-slate-400 dark:text-white/40'
          }`
        }
      >
        <LayoutDashboard className="w-4 h-4" />
        <span>Trang chủ</span>
      </NavLink>

      <NavLink
        to="/studio"
        className={`flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
          isStudio ? 'text-indigo-400 font-semibold' : 'text-slate-400 dark:text-white/40'
        }`}
      >
        <Mic className="w-4 h-4" />
        <span>Studio</span>
      </NavLink>

      <NavLink
        to="/voices"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
            isActive ? 'text-indigo-400 font-semibold' : 'text-slate-400 dark:text-white/40'
          }`
        }
      >
        <Volume2 className="w-4 h-4" />
        <span>Thư viện</span>
      </NavLink>

      <NavLink
        to="/history"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
            isActive ? 'text-indigo-400 font-semibold' : 'text-slate-400 dark:text-white/40'
          }`
        }
      >
        <History className="w-4 h-4" />
        <span>Lịch sử</span>
      </NavLink>

      <NavLink
        to="/profile"
        className={({ isActive }) =>
          `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${
            isActive ? 'text-indigo-400 font-semibold' : 'text-slate-400 dark:text-white/40'
          }`
        }
      >
        <User className="w-4 h-4" />
        <span>Tài khoản</span>
      </NavLink>
    </nav>
  )
}
