import { Link } from 'react-router-dom'
import { Coins, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface CreditChipProps {
  credits: number
  maxCredits?: number
  onTopUpClick?: () => void
}

export default function CreditChip({ credits, maxCredits = 10000, onTopUpClick }: CreditChipProps) {
  const { t } = useTranslation()

  // Tính tỷ lệ vòng tròn tiến độ (tối đa 100%)
  const percentage = Math.min(Math.round((credits / maxCredits) * 100), 100)
  const strokeDashoffset = 100 - percentage

  return (
    <div className="flex items-center gap-1.5 bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-control pl-2.5 pr-1 py-1 shadow-xs transition-all hover:border-indigo-500/30">
      {/* Vòng tròn tiến độ credit mini + số dư (bấm xem lịch sử) */}
      <Link
        to="/credits"
        className="flex items-center gap-1.5 group/chip hover:opacity-90 transition-opacity"
        title="Bấm để xem lịch sử biến động credit"
      >
        <div className="relative w-4 h-4 flex items-center justify-center flex-shrink-0" title={`${percentage}% hạn mức`}>
          <svg className="w-4 h-4 -rotate-90" viewBox="0 0 36 36">
            {/* Vòng nền */}
            <path
              className="text-slate-200 dark:text-white/10 stroke-current"
              strokeWidth="4"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            {/* Vòng màu hổ phách (amber) */}
            <path
              className="text-[#F59E0B] stroke-current transition-all duration-500 ease-out"
              strokeWidth="4"
              strokeDasharray="100, 100"
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <Coins className="w-2.5 h-2.5 text-[#F59E0B] absolute inset-auto" />
        </div>

        <div className="flex items-baseline gap-1 text-xs">
          <span className="text-slate-500 dark:text-white/50 text-[11px]">Còn</span>
          <span className="font-mono font-bold text-[#F59E0B] group-hover/chip:underline">
            {credits.toLocaleString('vi-VN')}
          </span>
        </div>
      </Link>

      {onTopUpClick ? (
        <button
          onClick={onTopUpClick}
          className="flex items-center gap-1 ml-1 px-2.5 py-1 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-[11px] font-semibold shadow-xs transition-all"
        >
          <Plus className="w-3 h-3" />
          <span>{t('common.topUp') || 'Nạp thêm'}</span>
        </button>
      ) : (
        <Link
          to="/pricing"
          className="flex items-center gap-1 ml-1 px-2.5 py-1 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-[11px] font-semibold shadow-xs transition-all"
        >
          <Plus className="w-3 h-3" />
          <span>{t('common.topUp') || 'Nạp thêm'}</span>
        </Link>
      )}
    </div>
  )
}
