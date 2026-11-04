import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiVerifyEmail } from '../api/auth'
import { useAppConfig } from '../hooks/useAppConfig'

export default function VerifyEmail() {
  const { config } = useAppConfig()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError('Thiếu mã xác thực trong đường dẫn.')
      setLoading(false)
      return
    }

    let isMounted = true
    apiVerifyEmail(token)
      .then((res) => {
        if (isMounted) {
          setSuccess(res.message || 'Xác thực tài khoản thành công!')
        }
      })
      .catch((err) => {
        if (isMounted) {
          const msg = err.response?.data?.detail || 'Mã xác thực không hợp lệ hoặc đã hết hạn.'
          setError(msg)
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [token])

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
          <h1 className="mt-4 text-xl font-bold text-white/90">Xác thực email</h1>
        </div>

        {/* Card */}
        <div className="bg-[#14141f] border border-white/10 rounded-2xl p-6 sm:p-8 shadow-xl text-center">
          {loading && (
            <div className="py-8">
              <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-white/70 text-sm">Đang xác thực tài khoản của bạn...</p>
            </div>
          )}

          {!loading && error && (
            <div className="py-4">
              <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 mx-auto flex items-center justify-center mb-3">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Xác thực thất bại</h3>
              <p className="text-sm text-red-400/90 mb-6">{error}</p>
              <Link
                to="/login"
                className="inline-block py-2.5 px-6 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium text-sm transition-colors"
              >
                Về trang Đăng nhập
              </Link>
            </div>
          )}

          {!loading && success && (
            <div className="py-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center mb-3">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Xác thực thành công</h3>
              <p className="text-sm text-white/60 mb-6">{success}</p>
              <Link
                to="/login"
                className="inline-block py-2.5 px-6 rounded-xl bg-gradient-to-r from-brand-500 to-purple-600 hover:from-brand-600 hover:to-purple-700 text-white font-medium text-sm transition-all shadow-lg shadow-brand-500/25"
              >
                Đăng nhập ngay
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

