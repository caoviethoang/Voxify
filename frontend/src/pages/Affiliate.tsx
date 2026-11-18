import { useState, useEffect, useCallback } from 'react'
import {
  Users,
  MousePointerClick,
  ShoppingBag,
  DollarSign,
  Copy,
  Check,
  Share2,
  Edit3,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Building,
  CreditCard,
  User,
  ShieldCheck,
} from 'lucide-react'
import {
  apiGetAffiliateDashboard,
  apiRequestWithdrawal,
  apiCustomizeReferralCode,
  type AffiliateDashboardResponse,
  type AffiliateCommissionItem,
  type AffiliateWithdrawalItem,
} from '../api/affiliate'
import { useToast } from '../hooks/useToast'

const VIETNAM_BANKS = [
  { code: 'MB', name: 'MBBank (Quân Đội)' },
  { code: 'VCB', name: 'Vietcombank (Ngoại Thương)' },
  { code: 'TCB', name: 'Techcombank (Kỹ Thương)' },
  { code: 'ACB', name: 'ACB (Á Châu)' },
  { code: 'VPB', name: 'VPBank (Việt Nam Thịnh Vượng)' },
  { code: 'TPB', name: 'TPBank (Tiên Phong)' },
  { code: 'BIDV', name: 'BIDV (Đầu Tư & Phát Triển)' },
  { code: 'CTG', name: 'VietinBank (Công Thương)' },
  { code: 'VBA', name: 'Agribank (Nông Nghiệp)' },
  { code: 'STB', name: 'Sacombank (Sài Gòn Thương Tín)' },
  { code: 'HDB', name: 'HDBank (Phát Triển TP.HCM)' },
  { code: 'OCB', name: 'OCB (Phương Đông)' },
  { code: 'SHB', name: 'SHB (Sài Gòn - Hà Nội)' },
  { code: 'MOMO', name: 'Ví điện tử MoMo' },
  { code: 'OTHER', name: 'Ngân hàng khác' },
]

export default function Affiliate() {
  const { success, error } = useToast()

  const [dashboard, setDashboard] = useState<AffiliateDashboardResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'commissions' | 'withdrawals'>('commissions')

  // Copy states
  const [copiedLink, setCopiedLink] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)

  // Modal Rút tiền
  const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false)
  const [withdrawAmount, setWithdrawAmount] = useState<string>('')
  const [bankName, setBankName] = useState<string>('MB')
  const [bankAccountNo, setBankAccountNo] = useState<string>('')
  const [bankAccountHolder, setBankAccountHolder] = useState<string>('')
  const [isSubmittingWithdraw, setIsSubmittingWithdraw] = useState(false)
  const [withdrawError, setWithdrawError] = useState<string | null>(null)

  // Modal đổi mã giới thiệu
  const [isCustomizeCodeModalOpen, setIsCustomizeCodeModalOpen] = useState(false)
  const [newCodeInput, setNewCodeInput] = useState<string>('')
  const [isSubmittingCode, setIsSubmittingCode] = useState(false)
  const [codeError, setCodeError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await apiGetAffiliateDashboard()
      setDashboard(data)
    } catch (err: unknown) {
      let msg = 'Không thể tải dữ liệu Affiliate.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        msg = axiosErr.response?.data?.detail || msg
      }
      error(msg)
    } finally {
      setIsLoading(false)
    }
  }, [error])

  useEffect(() => {
    loadData()
  }, [loadData])

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(amount)
  }

  const handleCopyLink = () => {
    if (!dashboard?.referral_link) return
    navigator.clipboard.writeText(dashboard.referral_link)
    setCopiedLink(true)
    success('Đã sao chép link giới thiệu vào bộ nhớ tạm!')
    setTimeout(() => setCopiedLink(false), 2000)
  }

  const handleCopyCode = () => {
    if (!dashboard?.referral_code) return
    navigator.clipboard.writeText(dashboard.referral_code)
    setCopiedCode(true)
    success('Đã sao chép mã giới thiệu vào bộ nhớ tạm!')
    setTimeout(() => setCopiedCode(false), 2000)
  }

  const handleShareFacebook = () => {
    if (!dashboard?.referral_link) return
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(dashboard.referral_link)}`
    window.open(url, '_blank', 'width=600,height=400')
  }

  const handleShareTwitter = () => {
    if (!dashboard?.referral_link) return
    const text = 'Chuyển văn bản thành giọng đọc AI chân thực cùng Voxify! Đăng ký ngay để nhận ưu đãi:'
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(dashboard.referral_link)}`
    window.open(url, '_blank', 'width=600,height=400')
  }

  const handleOpenWithdrawModal = () => {
    setWithdrawError(null)
    setWithdrawAmount(dashboard?.stats.available_commission?.toString() || '')
    setIsWithdrawModalOpen(true)
  }

  const handleSubmitWithdrawal = async (e: React.FormEvent) => {
    e.preventDefault()
    setWithdrawError(null)

    const amountNum = parseInt(withdrawAmount.replace(/\D/g, ''), 10)
    const minPayout = dashboard?.min_payout_amount || 200000

    if (isNaN(amountNum) || amountNum < minPayout) {
      setWithdrawError(`Số tiền rút tối thiểu là ${formatVND(minPayout)}.`)
      return
    }

    if (amountNum > (dashboard?.stats.available_commission || 0)) {
      setWithdrawError(`Số tiền rút vượt quá số dư khả dụng (${formatVND(dashboard?.stats.available_commission || 0)}).`)
      return
    }

    if (!bankAccountNo.trim() || !bankAccountHolder.trim()) {
      setWithdrawError('Vui lòng điền đầy đủ số tài khoản và tên chủ tài khoản.')
      return
    }

    try {
      setIsSubmittingWithdraw(true)
      const selectedBankObj = VIETNAM_BANKS.find(b => b.code === bankName)
      const bankLabel = selectedBankObj ? selectedBankObj.name : bankName

      await apiRequestWithdrawal({
        amount: amountNum,
        bank_name: bankLabel,
        bank_account_number: bankAccountNo.trim(),
        bank_account_holder: bankAccountHolder.trim().toUpperCase(),
      })

      success('Gửi yêu cầu rút tiền thành công! Admin sẽ duyệt trong 24-48h.')
      setIsWithdrawModalOpen(false)
      loadData()
    } catch (err: unknown) {
      let msg = 'Không thể gửi yêu cầu rút tiền.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        msg = axiosErr.response?.data?.detail || msg
      }
      setWithdrawError(msg)
    } finally {
      setIsSubmittingWithdraw(false)
    }
  }

  const handleSubmitCustomizeCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setCodeError(null)

    const cleanCode = newCodeInput.trim().toUpperCase()
    if (!/^[A-Z0-9_-]{4,20}$/.test(cleanCode)) {
      setCodeError('Mã giới thiệu chỉ được chứa chữ cái, số, dấu gạch ngang (4 - 20 ký tự).')
      return
    }

    try {
      setIsSubmittingCode(true)
      const res = await apiCustomizeReferralCode(cleanCode)
      success(res.message || 'Cập nhật mã giới thiệu thành công!')
      setIsCustomizeCodeModalOpen(false)
      loadData()
    } catch (err: unknown) {
      let msg = 'Không thể đổi mã giới thiệu.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        msg = axiosErr.response?.data?.detail || msg
      }
      setCodeError(msg)
    } finally {
      setIsSubmittingCode(false)
    }
  }

  const renderCommissionStatusBadge = (status: AffiliateCommissionItem['status']) => {
    switch (status) {
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Đã duyệt
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" />
            Tạm giữ (14 ngày)
          </span>
        )
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            Đã thu hồi (Refund)
          </span>
        )
      default:
        return <span>{status}</span>
    }
  }

  const renderWithdrawalStatusBadge = (status: AffiliateWithdrawalItem['status']) => {
    switch (status) {
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Đã chi trả
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3.5 h-3.5" />
            Đang xử lý
          </span>
        )
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            Từ chối
          </span>
        )
      default:
        return <span>{status}</span>
    }
  }

  if (isLoading && !dashboard) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-4">
        <div className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
        <p className="text-sm text-neutral-400">Đang tải dữ liệu Tiếp thị liên kết...</p>
      </div>
    )
  }

  const stats = dashboard?.stats || {
    total_clicks: 0,
    total_signups: 0,
    total_orders: 0,
    pending_commission: 0,
    available_commission: 0,
    withdrawn_commission: 0,
    total_earned_commission: 0,
  }

  const commissionRatePercent = Math.round((dashboard?.commission_rate || 0.25) * 100)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* 1. Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-purple-900/60 via-brand-900/40 to-neutral-900/80 border border-purple-500/20 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
              <span className="animate-pulse w-2 h-2 rounded-full bg-purple-400" />
              Chương trình Đối tác & Tiếp thị liên kết
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Nhận <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-amber-300">{commissionRatePercent}% Hoa Hồng Trọn Đời</span>
            </h1>
            <p className="text-sm sm:text-base text-neutral-300 leading-relaxed">
              Chia sẻ đường link Voxify đến bạn bè, cộng đồng sáng tạo nội dung hoặc khách hàng của bạn. Nhận hoa hồng trọn đời từ mọi giao dịch nâng cấp gói và nạp credit.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto">
            <button
              onClick={loadData}
              className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-neutral-300 text-sm font-medium transition-all flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Làm mới
            </button>
            <button
              onClick={handleOpenWithdrawModal}
              disabled={stats.available_commission < (dashboard?.min_payout_amount || 200000)}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold shadow-lg shadow-purple-600/25 transition-all flex items-center justify-center gap-2"
            >
              <ArrowUpRight className="w-4 h-4" />
              Rút tiền hoa hồng
            </button>
          </div>
        </div>
      </div>

      {/* 2. Referral Link & Code Sharing Box */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl bg-neutral-900/60 dark:bg-neutral-900/60 light:bg-white border border-neutral-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Share2 className="w-4 h-4 text-brand-400" />
              Đường link giới thiệu của bạn
            </h2>
            <span className="text-xs text-neutral-400">Cookie theo dõi 30 ngày</span>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                readOnly
                value={dashboard?.referral_link || ''}
                className="w-full bg-neutral-950/80 border border-neutral-700/80 rounded-xl px-4 py-3 text-sm font-mono text-neutral-200 select-all focus:outline-none"
              />
            </div>
            <button
              onClick={handleCopyLink}
              className="px-5 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors shadow-md"
            >
              {copiedLink ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
              {copiedLink ? 'Đã sao chép!' : 'Sao chép link'}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-neutral-400">
            <span>Chia sẻ nhanh:</span>
            <button
              onClick={handleShareFacebook}
              className="px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition-colors flex items-center gap-1.5"
            >
              Facebook
            </button>
            <button
              onClick={handleShareTwitter}
              className="px-3 py-1.5 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 transition-colors flex items-center gap-1.5"
            >
              X (Twitter)
            </button>
          </div>
        </div>

        {/* Mã giới thiệu riêng */}
        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-neutral-400">Mã giới thiệu (Ref Code)</span>
              <button
                onClick={() => {
                  setNewCodeInput(dashboard?.referral_code || '')
                  setCodeError(null)
                  setIsCustomizeCodeModalOpen(true)
                }}
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-colors"
              >
                <Edit3 className="w-3 h-3" />
                Đổi mã
              </button>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-neutral-950/80 border border-neutral-800">
              <span className="font-mono text-xl font-bold tracking-wider text-purple-300">
                {dashboard?.referral_code || '---'}
              </span>
              <button
                onClick={handleCopyCode}
                className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400 hover:text-white transition-colors"
                title="Sao chép mã"
              >
                {copiedCode ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <p className="text-xs text-neutral-400">
            Người dùng cũng có thể nhập trực tiếp mã này vào ô &ldquo;Mã giới thiệu&rdquo; khi đăng ký tài khoản.
          </p>
        </div>
      </div>

      {/* 3. Stat Cards & Wallet Box */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-5 space-y-2">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-xs font-medium">Lượt click link</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <MousePointerClick className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-extrabold text-white">
            {stats.total_clicks.toLocaleString('vi-VN')}
          </p>
          <span className="text-[11px] text-neutral-500">Số lần link được truy cập</span>
        </div>

        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-5 space-y-2">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-xs font-medium">Số người đăng ký</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-extrabold text-white">
            {stats.total_signups.toLocaleString('vi-VN')}
          </p>
          <span className="text-[11px] text-neutral-500">Tài khoản gắn mã giới thiệu</span>
        </div>

        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-5 space-y-2">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-xs font-medium">Đơn hàng thành công</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-extrabold text-white">
            {stats.total_orders.toLocaleString('vi-VN')}
          </p>
          <span className="text-[11px] text-neutral-500">Đơn hàng phát sinh hoa hồng</span>
        </div>

        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-5 space-y-2">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-xs font-medium">Tổng hoa hồng kiếm được</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl sm:text-3xl font-extrabold text-emerald-400">
            {formatVND(stats.total_earned_commission)}
          </p>
          <span className="text-[11px] text-neutral-500">Đã tích lũy thành công</span>
        </div>
      </div>

      {/* 4. Ví Hoa Hồng (Commission Wallet Overview) */}
      <div className="rounded-2xl bg-gradient-to-br from-neutral-900/90 via-neutral-900/60 to-purple-950/20 border border-neutral-800 p-6 sm:p-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-neutral-800">
          <div>
            <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Số dư khả dụng</span>
            <div className="flex items-baseline gap-3 mt-1">
              <span className="text-3xl sm:text-4xl font-black text-white">
                {formatVND(stats.available_commission)}
              </span>
              <span className="text-xs text-emerald-400 font-medium">Có thể rút ngay</span>
            </div>
          </div>

          <button
            onClick={handleOpenWithdrawModal}
            disabled={stats.available_commission < (dashboard?.min_payout_amount || 200000)}
            className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold shadow-lg shadow-brand-600/20 transition-all flex items-center gap-2"
          >
            <ArrowUpRight className="w-4 h-4" />
            Yêu cầu rút tiền về tài khoản
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-6 text-sm">
          <div className="flex items-center justify-between p-4 rounded-xl bg-neutral-950/50 border border-neutral-800/80">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-neutral-400 text-xs">
                <span>Đang chờ duyệt (Pending)</span>
                <span title="Tạm giữ 14 ngày để phòng ngừa hoàn tiền" className="cursor-help inline-flex items-center">
                  <HelpCircle className="w-3.5 h-3.5 text-neutral-500" />
                </span>
              </div>
              <p className="text-lg font-bold text-amber-300">{formatVND(stats.pending_commission)}</p>
            </div>
            <span className="text-xs text-amber-400/80 px-2.5 py-1 rounded-full bg-amber-400/10">14 ngày hold</span>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-neutral-950/50 border border-neutral-800/80">
            <div className="space-y-1">
              <span className="text-neutral-400 text-xs">Đã chi trả về tài khoản (Withdrawn)</span>
              <p className="text-lg font-bold text-neutral-200">{formatVND(stats.withdrawn_commission)}</p>
            </div>
            <span className="text-xs text-emerald-400/80 px-2.5 py-1 rounded-full bg-emerald-400/10">Đã thanh toán</span>
          </div>
        </div>
      </div>

      {/* 5. Data Tables (Tabs: Commissions vs Withdrawals) */}
      <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-neutral-800 bg-neutral-950/40">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('commissions')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'commissions'
                  ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
                  : 'text-neutral-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Lịch sử hoa hồng ({dashboard?.commissions.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('withdrawals')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'withdrawals'
                  ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
                  : 'text-neutral-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Lịch sử rút tiền ({dashboard?.withdrawals.length || 0})
            </button>
          </div>
        </div>

        {activeTab === 'commissions' ? (
          <div className="overflow-x-auto">
            {(!dashboard?.commissions || dashboard.commissions.length === 0) ? (
              <div className="py-16 text-center space-y-3">
                <ShoppingBag className="w-10 h-10 text-neutral-600 mx-auto" />
                <p className="text-sm text-neutral-400 font-medium">Chưa có giao dịch hoa hồng nào</p>
                <p className="text-xs text-neutral-500 max-w-sm mx-auto">
                  Hãy chia sẻ link giới thiệu đến bạn bè. Khi họ thanh toán đơn hàng đầu tiên, hoa hồng sẽ xuất hiện tại đây!
                </p>
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-950/80 text-neutral-400 uppercase tracking-wider text-[10px] border-b border-neutral-800">
                  <tr>
                    <th className="px-5 py-3.5">Mã đơn hàng</th>
                    <th className="px-5 py-3.5">Khách hàng</th>
                    <th className="px-5 py-3.5">Giá trị đơn</th>
                    <th className="px-5 py-3.5">Tỷ lệ</th>
                    <th className="px-5 py-3.5">Hoa hồng nhận</th>
                    <th className="px-5 py-3.5">Trạng thái</th>
                    <th className="px-5 py-3.5">Thời gian tạo</th>
                    <th className="px-5 py-3.5">Hết hạn tạm giữ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60 text-neutral-300 font-normal">
                  {dashboard.commissions.map((c) => (
                    <tr key={c.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-4 font-mono font-medium text-white">{c.order_code}</td>
                      <td className="px-5 py-4 font-mono text-neutral-400">{c.buyer_masked_email}</td>
                      <td className="px-5 py-4">{formatVND(c.order_amount)}</td>
                      <td className="px-5 py-4 font-medium text-purple-300">{Math.round(c.commission_rate * 100)}%</td>
                      <td className="px-5 py-4 font-bold text-emerald-400">{formatVND(c.amount)}</td>
                      <td className="px-5 py-4">{renderCommissionStatusBadge(c.status)}</td>
                      <td className="px-5 py-4 text-neutral-400">
                        {new Date(c.created_at).toLocaleDateString('vi-VN')}
                      </td>
                      <td className="px-5 py-4 text-neutral-400">
                        {new Date(c.hold_until).toLocaleDateString('vi-VN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            {(!dashboard?.withdrawals || dashboard.withdrawals.length === 0) ? (
              <div className="py-16 text-center space-y-3">
                <ArrowUpRight className="w-10 h-10 text-neutral-600 mx-auto" />
                <p className="text-sm text-neutral-400 font-medium">Chưa có yêu cầu rút tiền nào</p>
                <p className="text-xs text-neutral-500 max-w-sm mx-auto">
                  Khi tích lũy tối thiểu 200.000 VNĐ hoa hồng đã duyệt, bạn có thể gửi yêu cầu rút tiền về tài khoản ngân hàng.
                </p>
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-950/80 text-neutral-400 uppercase tracking-wider text-[10px] border-b border-neutral-800">
                  <tr>
                    <th className="px-5 py-3.5">Mã yêu cầu</th>
                    <th className="px-5 py-3.5">Thời gian gửi</th>
                    <th className="px-5 py-3.5">Số tiền rút</th>
                    <th className="px-5 py-3.5">Ngân hàng</th>
                    <th className="px-5 py-3.5">Số tài khoản</th>
                    <th className="px-5 py-3.5">Chủ tài khoản</th>
                    <th className="px-5 py-3.5">Trạng thái</th>
                    <th className="px-5 py-3.5">Ghi chú</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60 text-neutral-300 font-normal">
                  {dashboard.withdrawals.map((w) => (
                    <tr key={w.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-4 font-mono font-medium text-white">#W-{w.id}</td>
                      <td className="px-5 py-4 text-neutral-400">
                        {new Date(w.created_at).toLocaleDateString('vi-VN')}
                      </td>
                      <td className="px-5 py-4 font-bold text-white">{formatVND(w.amount)}</td>
                      <td className="px-5 py-4">{w.bank_name}</td>
                      <td className="px-5 py-4 font-mono">{w.bank_account_number}</td>
                      <td className="px-5 py-4 font-semibold uppercase">{w.bank_account_holder}</td>
                      <td className="px-5 py-4">{renderWithdrawalStatusBadge(w.status)}</td>
                      <td className="px-5 py-4 text-neutral-400 max-w-xs truncate">{w.note || '---'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* 6. Program Rules & Anti-Fraud Policy */}
      <div className="rounded-2xl bg-neutral-900/40 border border-neutral-800/80 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Chính sách Tiếp thị liên kết & Chống gian lận (Anti-fraud)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-neutral-400 leading-relaxed">
          <div className="space-y-2">
            <p className="flex items-start gap-2">
              <span className="text-purple-400 font-bold">•</span>
              <span><strong>Mức chia sẻ 25%:</strong> Hoa hồng được tính trực tiếp trên số tiền thực thanh toán của đơn hàng sau giảm giá.</span>
            </p>
            <p className="flex items-start gap-2">
              <span className="text-purple-400 font-bold">•</span>
              <span><strong>Cookie theo dõi 30 ngày:</strong> Khách nhấn vào link giới thiệu trong vòng 30 ngày đăng ký tài khoản đều được gắn referrer cho bạn.</span>
            </p>
            <p className="flex items-start gap-2">
              <span className="text-purple-400 font-bold">•</span>
              <span><strong>Thời gian tạm giữ 14 ngày:</strong> Để phòng ngừa rủi ro hoàn tiền/chargeback, hoa hồng ở trạng thái chờ duyệt 14 ngày trước khi tự động chuyển sang khả dụng.</span>
            </p>
          </div>
          <div className="space-y-2">
            <p className="flex items-start gap-2">
              <span className="text-purple-400 font-bold">•</span>
              <span><strong>Rút tiền tối thiểu:</strong> Hạn mức rút tiền tối thiểu là {formatVND(dashboard?.min_payout_amount || 200000)}. Thời gian chi trả từ 24 - 48h làm việc.</span>
            </p>
            <p className="flex items-start gap-2">
              <span className="text-purple-400 font-bold">•</span>
              <span><strong>Nghiêm cấm tự giới thiệu (Anti-fraud):</strong> Hệ thống tự động so khớp IP, email alias và dấu vân tay thiết bị. Hành vi tự giới thiệu sẽ bị hủy hoa hồng vĩnh viễn.</span>
            </p>
          </div>
        </div>
      </div>

      {/* Modal Rút Tiền */}
      {isWithdrawModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-[#14141f] border border-white/10 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-brand-400" />
                Rút tiền hoa hồng Affiliate
              </h3>
              <button
                onClick={() => setIsWithdrawModalOpen(false)}
                className="p-1 rounded-lg hover:bg-white/10 text-neutral-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {withdrawError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{withdrawError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitWithdrawal} className="space-y-4 text-xs">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="font-medium text-neutral-300">Số tiền muốn rút (VNĐ) *</label>
                  <button
                    type="button"
                    onClick={() => setWithdrawAmount((dashboard?.stats.available_commission || 0).toString())}
                    className="text-[11px] text-brand-400 hover:underline"
                  >
                    Rút tất cả ({formatVND(dashboard?.stats.available_commission || 0)})
                  </button>
                </div>
                <input
                  type="number"
                  min={dashboard?.min_payout_amount || 200000}
                  max={dashboard?.stats.available_commission || 0}
                  step={1000}
                  value={withdrawAmount}
                  onChange={e => setWithdrawAmount(e.target.value)}
                  placeholder="Ví dụ: 500000"
                  required
                  className="w-full bg-neutral-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white font-mono placeholder:text-neutral-600 focus:outline-none focus:border-brand-500"
                />
                <span className="text-[11px] text-neutral-400 mt-1 block">
                  Tối thiểu: {formatVND(dashboard?.min_payout_amount || 200000)}
                </span>
              </div>

              <div>
                <label className="font-medium text-neutral-300 mb-1.5 block flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-neutral-400" />
                  Ngân hàng thụ hưởng *
                </label>
                <select
                  value={bankName}
                  onChange={e => setBankName(e.target.value)}
                  className="w-full bg-neutral-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
                >
                  {VIETNAM_BANKS.map(b => (
                    <option key={b.code} value={b.code}>{b.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-medium text-neutral-300 mb-1.5 block flex items-center gap-1.5">
                  <CreditCard className="w-3.5 h-3.5 text-neutral-400" />
                  Số tài khoản ngân hàng *
                </label>
                <input
                  type="text"
                  value={bankAccountNo}
                  onChange={e => setBankAccountNo(e.target.value)}
                  placeholder="Ví dụ: 0333888999"
                  required
                  className="w-full bg-neutral-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white font-mono placeholder:text-neutral-600 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="font-medium text-neutral-300 mb-1.5 block flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-neutral-400" />
                  Tên chủ tài khoản (In hoa không dấu) *
                </label>
                <input
                  type="text"
                  value={bankAccountHolder}
                  onChange={e => setBankAccountHolder(e.target.value.toUpperCase())}
                  placeholder="NGUYEN VAN A"
                  required
                  className="w-full bg-neutral-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white uppercase placeholder:text-neutral-600 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsWithdrawModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl border border-white/10 text-neutral-300 hover:bg-white/5 text-xs font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingWithdraw}
                  className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md flex items-center gap-2"
                >
                  {isSubmittingWithdraw ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Đang xử lý...
                    </>
                  ) : (
                    'Xác nhận rút tiền'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Đổi Mã Giới Thiệu */}
      {isCustomizeCodeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-sm rounded-2xl bg-[#14141f] border border-white/10 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-purple-400" />
                Tùy chỉnh mã giới thiệu
              </h3>
              <button
                onClick={() => setIsCustomizeCodeModalOpen(false)}
                className="p-1 rounded-lg hover:bg-white/10 text-neutral-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {codeError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{codeError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitCustomizeCode} className="space-y-4 text-xs">
              <div>
                <label className="font-medium text-neutral-300 mb-1.5 block">
                  Mã giới thiệu mới (4 - 20 ký tự) *
                </label>
                <input
                  type="text"
                  value={newCodeInput}
                  onChange={e => setNewCodeInput(e.target.value.toUpperCase())}
                  placeholder="Ví dụ: MYBRAND2026"
                  required
                  maxLength={20}
                  className="w-full bg-neutral-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white font-mono uppercase placeholder:text-neutral-600 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[11px] text-neutral-400 mt-1 block">
                  Chỉ gồm chữ in hoa, chữ số và dấu gạch ngang (-).
                </span>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCustomizeCodeModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 text-neutral-300 hover:bg-white/5 text-xs font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCode}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md flex items-center gap-2"
                >
                  {isSubmittingCode ? 'Đang lưu...' : 'Lưu mã mới'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
