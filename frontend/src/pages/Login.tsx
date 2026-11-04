import React, { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { login, googleLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const googleBtnRef = useRef<HTMLDivElement>(null)
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

  // Khởi tạo Google Identity Services nếu có Client ID
  useEffect(() => {
    if (!googleClientId) return

    let checkInterval: any = null

    const initGsi = () => {
      if (window.google?.accounts?.id && googleBtnRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: async (response) => {
              if (response.credential) {
                setIsLoading(true)
                setError(null)
                try {
                  await googleLogin(response.credential)
                  navigate(from, { replace: true })
                } catch (err: unknown) {
                  let msg = 'Đăng nhập Google thất bại.'
                  if (err && typeof err === 'object' && 'response' in err) {
                    const axiosErr = err as { response?: { data?: { detail?: string } } }
                    msg = axiosErr.response?.data?.detail || msg
                  }
                  setError(msg)
                } finally {
                  setIsLoading(false)
                }
              }
            },
          })

          googleBtnRef.current.innerHTML = ''
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            theme: 'filled_black',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            width: 384,
            locale: 'vi',
          })
          if (checkInterval) clearInterval(checkInterval)
        } catch {
          // Bỏ qua lỗi khởi tạo nếu chưa sẵn sàng
        }
      }
    }

    initGsi()
    checkInterval = setInterval(initGsi, 500)
    return () => {
      if (checkInterval) clearInterval(checkInterval)
    }
  }, [googleClientId, googleLogin, navigate, from])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Vui lòng nhập đầy đủ email và mật khẩu.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      await login({ email, password })
      navigate(from, { replace: true })
    } catch (err: unknown) {
      let msg = 'Đăng nhập không thành công.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        msg = axiosErr.response?.data?.detail || msg
      } else if (err instanceof Error) {
        msg = err.message
      }
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  // Google Sign-in click handler khi chưa có Client ID hoặc GIS chưa gắn nút tự động
  const handleManualGoogleClick = () => {
    setError(null)
    if (!googleClientId) {
      setError('Chức năng Đăng nhập Google chưa được kích hoạt do chưa cấu hình VITE_GOOGLE_CLIENT_ID trong file .env.')
      return
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt()
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-[#14141f] rounded-2xl border border-white/5 p-8 shadow-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-brand-500/25">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Đăng nhập tài khoản</h2>
          <p className="text-xs text-white/40 mt-1">Đăng nhập để sử dụng toàn bộ tính năng tổng hợp giọng nói</p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="flex-shrink-0">
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-white/70 mb-1.5">Địa chỉ Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="tenban@example.com"
              required
              className="w-full bg-[#0f0f1a] border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-brand-500/40 transition-colors"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-white/70">Mật khẩu</label>
              <Link to="/forgot-password" className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                Quên mật khẩu?
              </Link>
            </div>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full bg-[#0f0f1a] border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-brand-500/40 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-brand-600/25 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Đang xử lý...
              </>
            ) : (
              'Đăng nhập'
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/5" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-[#14141f] px-3 text-white/30">hoặc</span>
          </div>
        </div>

        {/* Google OAuth Container */}
        {googleClientId ? (
          <div className="flex justify-center w-full min-h-[44px]">
            <div ref={googleBtnRef} className="w-full flex justify-center" />
          </div>
        ) : (
          <button
            type="button"
            onClick={handleManualGoogleClick}
            disabled={isLoading}
            className="w-full py-2.5 border border-white/10 hover:border-white/20 hover:bg-white/5 text-white/80 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-2.5 cursor-pointer"
          >
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 10.8 0 12s.7 2.3 1.9 4.7l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2-6.4-4.8L1.9 16.4C3.7 20.1 7.5 23 12 23z"
              />
            </svg>
            Đăng nhập với Google
          </button>
        )}

        {/* Register link */}
        <p className="text-center text-xs text-white/40 mt-6">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium transition-colors">
            Đăng ký ngay
          </Link>
        </p>
      </div>
    </div>
  )
}
