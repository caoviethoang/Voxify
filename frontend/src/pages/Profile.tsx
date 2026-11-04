import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { User, Mail, Shield, Coins, CheckCircle, Calendar } from 'lucide-react'

export default function Profile() {
  const { t } = useTranslation()
  const { user } = useAuth()

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Chưa xác định'
    try {
      return new Date(dateString).toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateString
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-4 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {t('profile.title')}
        </h1>
        <p className="text-xs text-slate-500 dark:text-white/40 mt-1">
          Thông tin chi tiết về tài khoản và hạn mức sử dụng dịch vụ Voxify của bạn.
        </p>
      </div>

      <div className="bg-white dark:bg-[#141422] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm space-y-6">
        {/* User Card Header */}
        <div className="flex items-center gap-4 pb-6 border-b border-slate-100 dark:border-white/5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-500 to-purple-600 flex items-center justify-center text-white text-xl font-extrabold shadow-lg shadow-brand-500/25">
            {user?.full_name ? user.full_name[0].toUpperCase() : user?.email[0].toUpperCase()}
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {user?.full_name || 'Người dùng Voxify'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-white/40">{user?.email}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 inline-flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                {t('profile.active')}
              </span>
              {user?.role === 'admin' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  ADMIN
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Detailed Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3">
            <Mail className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <span className="text-[11px] font-medium text-slate-400 dark:text-white/40 block">
                {t('profile.email')}
              </span>
              <span className="text-xs font-semibold text-slate-800 dark:text-white">
                {user?.email}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3">
            <User className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <span className="text-[11px] font-medium text-slate-400 dark:text-white/40 block">
                {t('profile.fullName')}
              </span>
              <span className="text-xs font-semibold text-slate-800 dark:text-white">
                {user?.full_name || '(Chưa cập nhật)'}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3">
            <Coins className="w-5 h-5 text-amber-500 mt-0.5" />
            <div>
              <span className="text-[11px] font-medium text-slate-400 dark:text-white/40 block">
                {t('profile.credits')}
              </span>
              <span className="text-sm font-bold text-amber-500">
                {user?.credits.toLocaleString('vi-VN')} credit
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3">
            <Shield className="w-5 h-5 text-purple-400 mt-0.5" />
            <div>
              <span className="text-[11px] font-medium text-slate-400 dark:text-white/40 block">
                {t('profile.role')}
              </span>
              <span className="text-xs font-semibold uppercase text-slate-800 dark:text-white">
                {user?.role}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3 sm:col-span-2">
            <Calendar className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <span className="text-[11px] font-medium text-slate-400 dark:text-white/40 block">
                {t('profile.joinedAt')}
              </span>
              <span className="text-xs font-semibold text-slate-800 dark:text-white">
                {formatDate(user?.created_at)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
