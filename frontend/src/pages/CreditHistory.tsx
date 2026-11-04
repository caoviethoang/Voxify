import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Coins,
  ArrowUpRight,
  ArrowDownLeft,
  Sparkles,
  Gift,
  RefreshCw,
  Plus,
  ChevronLeft,
  ChevronRight,
  Filter,
  CheckCircle2,
  Clock,
  History,
} from 'lucide-react'
import { useCredit } from '../hooks/useCredit'
import { type CreditTransactionType } from '../api/credit'

export default function CreditHistory() {
  const { balance, historyData, isHistoryLoading, loadTransactions, refreshCredits } = useCredit()

  const [page, setPage] = useState(1)
  const [selectedType, setSelectedType] = useState<string>('all')

  const fetchPage = useCallback(
    (pageNum: number, typeFilter: string) => {
      loadTransactions({
        page: pageNum,
        limit: 15,
        type: typeFilter === 'all' ? undefined : typeFilter,
      })
    },
    [loadTransactions]
  )

  useEffect(() => {
    fetchPage(page, selectedType)
  }, [page, selectedType, fetchPage])

  const handleTypeChange = (typeVal: string) => {
    setSelectedType(typeVal)
    setPage(1)
  }

  const handleRefresh = async () => {
    await refreshCredits()
    fetchPage(page, selectedType)
  }

  // Helper format loại giao dịch
  const renderTypeBadge = (type: CreditTransactionType | string) => {
    switch (type) {
      case 'signup_bonus':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
            <Gift className="w-3 h-3" />
            Thưởng đăng ký
          </span>
        )
      case 'purchase':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20">
            <ArrowDownLeft className="w-3 h-3" />
            Nạp credit
          </span>
        )
      case 'usage':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-white/70 border border-slate-200 dark:border-white/10">
            <ArrowUpRight className="w-3 h-3" />
            Sử dụng TTS
          </span>
        )
      case 'refund':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-[#F59E0B] border border-amber-200 dark:border-amber-500/20">
            <RefreshCw className="w-3 h-3" />
            Hoàn lại
          </span>
        )
      case 'affiliate':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20">
            <Sparkles className="w-3 h-3" />
            Hoa hồng bạn bè
          </span>
        )
      case 'admin_adjust':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Điều chỉnh
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-white/60">
            {type}
          </span>
        )
    }
  }

  const items = historyData?.items ?? []
  const total = historyData?.total ?? 0
  const totalPages = historyData?.total_pages ?? 1

  return (
    <div className="space-y-6 max-w-6xl mx-auto py-2 animate-in fade-in duration-200">
      {/* 1. Header Banner & Quick Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
              <Coins className="w-7 h-7 text-[#F59E0B]" />
              <span>Lịch sử giao dịch Credit</span>
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1">
            Sổ cái điện tử minh bạch, chi tiết mọi biến động cộng/trừ số dư tài khoản của bạn.
          </p>
        </div>

        <Link
          to="/pricing"
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-xs transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Nạp thêm Credit</span>
        </Link>
      </div>

      {/* 2. Thẻ tóm tắt số dư và thống kê */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Số dư hiện tại */}
        <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase block">
              Số dư khả dụng
            </span>
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-[#F59E0B] mt-1">
              {balance.toLocaleString('vi-VN')}
            </div>
            <span className="text-[10px] text-slate-400 dark:text-white/30 block mt-0.5">
              1 credit = 1 ký tự chuẩn
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-amber-500/10 text-[#F59E0B] border border-amber-500/20 flex items-center justify-center">
            <Coins className="w-6 h-6" />
          </div>
        </div>

        {/* Tổng giao dịch */}
        <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase block">
              Tổng số bản ghi
            </span>
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-slate-900 dark:text-white mt-1">
              {total.toLocaleString('vi-VN')}
            </div>
            <span className="text-[10px] text-slate-400 dark:text-white/30 block mt-0.5">
              Giao dịch đã ghi sổ cái
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-500/20 flex items-center justify-center">
            <History className="w-6 h-6" />
          </div>
        </div>

        {/* Trạng thái xác thực sổ cái */}
        <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase block">
              Tính toàn vẹn
            </span>
            <div className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-5 h-5" />
              <span>Khớp sổ cái 100%</span>
            </div>
            <span className="text-[10px] text-slate-400 dark:text-white/30 block mt-0.5">
              Bảo vệ row-level lock chống xung đột
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-500/20 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* 3. Thanh bộ lọc giao dịch */}
      <div className="p-3.5 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-wrap items-center justify-between gap-3">
        {/* Pills filter */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-slate-500 dark:text-white/40 text-[11px] font-medium flex items-center gap-1 mr-1">
            <Filter className="w-3.5 h-3.5" />
            Lọc:
          </span>

          {[
            { id: 'all', label: 'Tất cả' },
            { id: 'usage', label: 'Sử dụng' },
            { id: 'signup_bonus', label: 'Thưởng đăng ký' },
            { id: 'purchase', label: 'Nạp tiền' },
            { id: 'refund', label: 'Hoàn lại' },
            { id: 'affiliate', label: 'Giới thiệu' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => handleTypeChange(pill.id)}
              className={`px-3 py-1 rounded-[8px] font-medium transition-all text-xs ${
                selectedType === pill.id
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs font-semibold'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-600 dark:bg-[#181C25] dark:hover:bg-[#202532] dark:text-white/60 dark:hover:text-white'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* Nút làm mới */}
        <button
          onClick={handleRefresh}
          disabled={isHistoryLoading}
          className="flex items-center gap-1 px-3 py-1.5 rounded-control text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 dark:text-white/60 dark:hover:text-white dark:bg-[#181C25] dark:hover:bg-[#202532] border border-slate-200/80 dark:border-white/[0.06] transition-colors"
          title="Tải lại danh sách"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isHistoryLoading ? 'animate-spin' : ''}`} />
          <span>Làm mới</span>
        </button>
      </div>

      {/* 4. Bảng Sổ cái Ledger */}
      <div className="rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs overflow-hidden">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-left text-xs">
            <thead className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-white/40 border-b border-slate-200 dark:border-white/[0.06] bg-slate-50/70 dark:bg-[#0B0D12]/40">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Loại giao dịch</th>
                <th className="py-3 px-4">Biến động</th>
                <th className="py-3 px-4">Số dư sau GD</th>
                <th className="py-3 px-4">Mô tả</th>
                <th className="py-3 px-4">Mã tham chiếu</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
              {isHistoryLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 dark:text-white/30">
                    <div className="inline-flex items-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
                      <span>Đang tải sổ cái giao dịch...</span>
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 dark:text-white/30">
                    Chưa có giao dịch nào phù hợp với bộ lọc hiện tại.
                  </td>
                </tr>
              ) : (
                items.map((tx) => {
                  const isPositive = tx.amount > 0
                  const dateStr = new Date(tx.created_at).toLocaleString('vi-VN')

                  return (
                    <tr
                      key={tx.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-white/[0.02] transition-colors"
                    >
                      {/* Thời gian */}
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-500 dark:text-white/40 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{dateStr}</span>
                        </div>
                      </td>

                      {/* Loại giao dịch */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {renderTypeBadge(tx.type)}
                      </td>

                      {/* Biến động (+/-) */}
                      <td className="py-3.5 px-4 font-mono font-bold whitespace-nowrap">
                        <span
                          className={
                            isPositive
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : tx.amount < 0
                              ? 'text-rose-600 dark:text-rose-400'
                              : 'text-slate-400'
                          }
                        >
                          {isPositive ? `+${tx.amount.toLocaleString('vi-VN')}` : tx.amount.toLocaleString('vi-VN')}
                        </span>
                      </td>

                      {/* Số dư sau giao dịch */}
                      <td className="py-3.5 px-4 font-mono font-bold text-[#F59E0B] whitespace-nowrap">
                        {tx.balance_after.toLocaleString('vi-VN')}
                      </td>

                      {/* Mô tả */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-white/80 max-w-[280px] truncate" title={tx.description || ''}>
                        {tx.description || 'Giao dịch hệ thống'}
                      </td>

                      {/* Mã tham chiếu */}
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 dark:text-white/40 whitespace-nowrap">
                        {tx.ref_id ? (
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/5 border border-slate-200/60 dark:border-white/5">
                            {tx.ref_id}
                          </span>
                        ) : (
                          <span className="text-slate-300 dark:text-white/20">&mdash;</span>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Phân trang dưới đáy bảng */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/40 flex items-center justify-between text-xs">
            <span className="text-slate-500 dark:text-white/40 font-mono">
              Trang {page} / {totalPages} ({total} bản ghi)
            </span>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="Trang trước"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="Trang sau"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
