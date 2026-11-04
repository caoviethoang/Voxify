import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { apiResetPassword } from '../api/auth'
import { useAppConfig } from '../hooks/useAppConfig'

export default function ResetPassword() {
  const { config } = useAppConfig()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!token) {
      setError('Mã xác thực không hợp lệ hoặc đã thiếu trong đường dẫn.')
      return
    }

    if (newPassword.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.')
      return
    }

    try {
      setLoading(true)
      const res = await apiResetPassword(token, newPassword)
      setSuccess(res.message || 'Đặt lại mật khẩu thành công!')
      setTimeout(() => {
        navigate('/login')
      }, 2500)
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Không thể đặt lại mật khẩu. Vui lòng thử lại.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Brand logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/25">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="8" y1="22" x2="16" y2="22" />
              </svg>
            </div>
            <span className="font-bold text-2xl tracking-tight">{config.app_name}</span>
          </Link>
          <h1 className="mt-4 text-xl font-bold text-white/90">Đặt lại mật khẩu</h1>
          <p className="mt-1 text-sm text-white/50">
            Nhập mật khẩu mới an toàn cho tài khoản của bạn
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#14141f] border border-white/10 rounded-2xl p-6 sm:p-8 shadow-xl">
          {!token ? (
            <div className="text-center">
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm mb-4">
                Đường dẫn đặt lại mật khẩu không hợp lệ hoặc thiếu mã xác thực.
              </div>
              <Link
                to="/forgot-password"
                className="inline-block py-2.5 px-4 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-medium text-sm transition-colors"
              >
                Yêu cầu gửi lại link mới
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-start gap-2">
                  <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              {success ? (
                <div className="text-center py-4">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center mb-3">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-base font-semibold text-white mb-2">{success}</h3>
                  <p className="text-sm text-white/50 mb-4">Đang chuyển hướng về trang đăng nhập...</p>
                  <Link
                    to="/login"
                    className="inline-block py-2.5 px-5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-medium text-sm transition-colors"
                  >
                    Đăng nhập ngay
                  </Link>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-white/70 mb-1.5">
                      Mật khẩu mới
                    </label>
                    <input
                      type="password"
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Ít nhất 6 ký tự"
                      className="w-full bg-[#1b1b2a] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-brand-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-white/70 mb-1.5">
                      Xác nhận mật khẩu mới
                    </label>
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Nhập lại mật khẩu mới"
                      className="w-full bg-[#1b1b2a] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-brand-500 transition-colors"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-purple-600 hover:from-brand-600 hover:to-purple-700 text-white font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-brand-500/20"
                  >
                    {loading ? 'Đang cập nhật...' : 'Cập nhật mật khẩu'}
                  </button>
                </form>
              )}
            </>
          )}
        </div>

        <div className="mt-6 text-center text-sm text-white/40">
          <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">
            &larr; Quay lại Đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
