import { Link, Outlet } from 'react-router-dom'
import { useAppConfig } from '../hooks/useAppConfig'
import { useAuth } from '../hooks/useAuth'

export default function AppLayout() {
  const { config } = useAppConfig()
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-white/5 bg-[#14141f]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/25">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                  <line x1="8" y1="22" x2="16" y2="22" />
                </svg>
              </div>
              <span className="font-bold text-lg tracking-tight">{config.app_name}</span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-xs text-emerald-400 bg-emerald-400/10 px-3 py-1.5 rounded-full border border-emerald-400/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Engine: Edge-TTS
            </div>

            {isAuthenticated && user ? (
              <div className="flex items-center gap-3">
                <div className="hidden md:flex items-center gap-2 bg-[#1b1b2a] border border-white/10 px-3 py-1.5 rounded-full text-xs">
                  <span className="text-white/50">Credits:</span>
                  <span className="font-semibold text-brand-400">
                    {user.credits.toLocaleString('vi-VN')}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {user.role === 'admin' && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      ADMIN
                    </span>
                  )}
                  <span className="text-xs text-white/80 max-w-[140px] truncate hidden sm:inline" title={user.email}>
                    {user.full_name || user.email}
                  </span>
                </div>

                <button
                  onClick={logout}
                  className="text-xs text-white/60 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-lg transition-colors"
                  title="Đăng xuất"
                >
                  Đăng xuất
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-xs text-white/80 hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
                >
                  Đăng nhập
                </Link>
                <Link
                  to="/register"
                  className="text-xs bg-brand-500 hover:bg-brand-600 text-white font-medium px-3 py-1.5 rounded-lg transition-colors shadow-sm shadow-brand-500/30"
                >
                  Đăng ký
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 text-center text-xs text-white/30">
        {config.app_name} &copy; 2026 &middot; Bản phát triển thử nghiệm Text-to-Speech tiếng Việt
      </footer>
    </div>
  )
}

