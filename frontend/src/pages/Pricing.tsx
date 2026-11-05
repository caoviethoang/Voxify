import { useState, useEffect, useCallback, useId } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Sparkles,
  Zap,
  Check,
  ShieldCheck,
  Copy,
  CheckCircle2,
  Clock,
  ArrowRight,
  QrCode,
  CreditCard,
  Download,
  RefreshCw,
  X,
  FileText,
  Lock,
  ExternalLink,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import {
  type PricingPlan,
  type Order,
  type CouponValidateResult,
  apiGetPlans,
  apiValidateCoupon,
  apiCreateOrder,
  apiGetOrder,
  apiGetMyOrders,
  apiCancelOrder,
  apiDownloadReceipt,
  apiSimulateSandboxPayment,
  apiPayWithCard,
} from '../api/payment'

export default function Pricing() {
  const { user, refreshUser } = useAuth()
  const { success, error, info } = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Tab: 'plans' | 'orders'
  const activeTab = searchParams.get('tab') === 'orders' ? 'orders' : 'plans'
  const planTypeTab = (searchParams.get('type') as 'credit_pack' | 'subscription') || 'credit_pack'

  // Data states
  const [plans, setPlans] = useState<PricingPlan[]>([])
  const [isLoadingPlans, setIsLoadingPlans] = useState(true)
  const [orders, setOrders] = useState<Order[]>([])
  const [ordersTotal, setOrdersTotal] = useState(0)
  const [ordersPage, setOrdersPage] = useState(1)
  const [isLoadingOrders, setIsLoadingOrders] = useState(false)

  // Checkout Modal State
  const [selectedPlan, setSelectedPlan] = useState<PricingPlan | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<'vietqr' | 'payos' | 'stripe'>('vietqr')
  const [couponCode, setCouponCode] = useState('')
  const [couponResult, setCouponResult] = useState<CouponValidateResult | null>(null)
  const [isValidatingCoupon, setIsValidatingCoupon] = useState(false)
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false)

  // Realtime Active Order Modal
  const [activeOrder, setActiveOrder] = useState<Order | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [isSimulatingPayment, setIsSimulatingPayment] = useState(false)
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState<number>(1800) // 30 mins in seconds

  // Credit Card Form State (Stripe)
  const [cardNumber, setCardNumber] = useState('4242 4242 4242 4242')
  const [cardHolder, setCardHolder] = useState(user?.full_name?.toUpperCase() || 'NGUYEN VAN A')
  const [cardExpMonth, setCardExpMonth] = useState('12')
  const [cardExpYear, setCardExpYear] = useState('28')
  const [cardCvc, setCardCvc] = useState('123')
  const [isProcessingCard, setIsProcessingCard] = useState(false)

  const couponInputId = useId()

  // Load Pricing Plans
  const fetchPlans = useCallback(async () => {
    try {
      setIsLoadingPlans(true)
      const data = await apiGetPlans()
      setPlans(data)
    } catch {
      error('Không thể tải danh sách gói cước. Vui lòng thử lại sau.')
    } finally {
      setIsLoadingPlans(false)
    }
  }, [error])

  // Load User Orders
  const fetchOrders = useCallback(
    async (page = 1) => {
      try {
        setIsLoadingOrders(true)
        const res = await apiGetMyOrders(page, 10)
        setOrders(res.orders)
        setOrdersTotal(res.total)
        setOrdersPage(res.page)
      } catch {
        error('Không thể tải danh sách hóa đơn.')
      } finally {
        setIsLoadingOrders(false)
      }
    },
    [error]
  )

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  useEffect(() => {
    if (activeTab === 'orders') {
      fetchOrders(ordersPage)
    }
  }, [activeTab, ordersPage, fetchOrders])

  // Handle return redirect from Stripe or PayOS (e.g. ?order_id=VOX123&status=success)
  useEffect(() => {
    const orderIdParam = searchParams.get('order_id')
    const statusParam = searchParams.get('status')
    if (orderIdParam && statusParam === 'success') {
      apiGetOrder(orderIdParam)
        .then((ord) => {
          setActiveOrder(ord)
          refreshUser()
        })
        .catch(() => {})
    }
  }, [searchParams, refreshUser])

  // Realtime Polling for Active Pending Order
  useEffect(() => {
    if (!activeOrder || activeOrder.status !== 'pending') return

    const interval = setInterval(async () => {
      try {
        const fresh = await apiGetOrder(activeOrder.id)
        if (fresh.status !== activeOrder.status) {
          setActiveOrder(fresh)
          if (fresh.status === 'paid') {
            await refreshUser()
            success(
              `Thanh toán thành công! Đã cộng +${fresh.credits_to_add.toLocaleString()} credit vào tài khoản.`
            )
            // Refresh order list if orders tab is open
            if (activeTab === 'orders') {
              fetchOrders(ordersPage)
            }
          }
        }
      } catch {
        // Silent poll error
      }
    }, 2500)

    return () => clearInterval(interval)
  }, [activeOrder, refreshUser, success, activeTab, ordersPage, fetchOrders])

  // Countdown timer for pending order
  useEffect(() => {
    if (!activeOrder || activeOrder.status !== 'pending') return

    const expiryMs = new Date(activeOrder.expires_at).getTime()
    const updateCountdown = () => {
      const now = Date.now()
      const diffSecs = Math.max(0, Math.floor((expiryMs - now) / 1000))
      setTimeRemaining(diffSecs)
    }

    updateCountdown()
    const timer = setInterval(updateCountdown, 1000)
    return () => clearInterval(timer)
  }, [activeOrder])

  // Handle Tab Switch
  const handleSwitchTab = (tab: 'plans' | 'orders') => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      p.set('tab', tab)
      return p
    })
  }

  const handleSwitchPlanType = (type: 'credit_pack' | 'subscription') => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      p.set('type', type)
      return p
    })
  }

  // Handle Validate Coupon
  const handleValidateCoupon = async () => {
    if (!couponCode.trim() || !selectedPlan) return
    try {
      setIsValidatingCoupon(true)
      const res = await apiValidateCoupon(couponCode.trim(), selectedPlan.price)
      setCouponResult(res)
      if (res.valid) {
        success(res.message)
      } else {
        error(res.message)
      }
    } catch {
      error('Không thể kiểm tra mã giảm giá')
    } finally {
      setIsValidatingCoupon(false)
    }
  }

  // Handle Open Checkout Modal
  const handleSelectPlan = (plan: PricingPlan) => {
    if (plan.price === 0) {
      info('Gói Miễn Phí đã được kích hoạt sẵn cho tài khoản của bạn.')
      return
    }
    setSelectedPlan(plan)
    setCouponCode('')
    setCouponResult(null)
    setPaymentMethod('vietqr')
  }

  // Handle Submit Order
  const handleCreateOrder = async () => {
    if (!selectedPlan) return
    try {
      setIsSubmittingOrder(true)
      const newOrder = await apiCreateOrder({
        plan_id: selectedPlan.id,
        payment_method: paymentMethod,
        coupon_code: couponResult?.valid ? couponResult.code : undefined,
      })
      setSelectedPlan(null)
      setActiveOrder(newOrder)
      info('Đã tạo đơn hàng. Vui lòng quét mã QR để thanh toán.')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Tạo đơn hàng thất bại. Vui lòng thử lại.'
      error(msg)
    } finally {
      setIsSubmittingOrder(false)
    }
  }

  // Handle Simulate Sandbox Payment
  const handleSimulatePayment = async () => {
    if (!activeOrder) return
    try {
      setIsSimulatingPayment(true)
      const res = await apiSimulateSandboxPayment(activeOrder.id)
      setActiveOrder(res.order)
      await refreshUser()
      success(
        `Mô phỏng thành công! Đã cộng +${res.order.credits_to_add.toLocaleString()} credit vào tài khoản.`
      )
    } catch {
      error('Mô phỏng thất bại. Vui lòng thử lại.')
    } finally {
      setIsSimulatingPayment(false)
    }
  }

  // Handle Download PDF Receipt
  const handleDownloadReceipt = async (order: Order) => {
    try {
      setIsDownloadingPdf(true)
      await apiDownloadReceipt(order.id, order.order_code)
      success('Đã tải biên lai PDF thành công!')
    } catch {
      error('Không thể tải biên lai PDF.')
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  // Handle Cancel Order
  const handleCancelOrder = async (orderId: number) => {
    try {
      await apiCancelOrder(orderId)
      info('Đã hủy đơn hàng thành công.')
      if (activeOrder && activeOrder.id === orderId) {
        setActiveOrder(null)
      }
      fetchOrders(ordersPage)
    } catch {
      error('Không thể hủy đơn hàng.')
    }
  }

  // Handle Pay With Credit Card (Stripe)
  const handlePayWithCard = async () => {
    if (!activeOrder) return
    try {
      setIsProcessingCard(true)
      const cleanNum = cardNumber.replace(/\s+/g, '')
      const updated = await apiPayWithCard(activeOrder.id, {
        card_number: cleanNum,
        cardholder_name: cardHolder,
        exp_month: cardExpMonth,
        exp_year: cardExpYear,
        cvc: cardCvc,
      })
      setActiveOrder(updated)
      await refreshUser()
      success(
        `Thanh toán thẻ thành công! Đã cộng +${updated.credits_to_add.toLocaleString()} credit vào tài khoản.`
      )
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Thanh toán thẻ thất bại. Vui lòng kiểm tra lại thông tin.'
      error(msg)
    } finally {
      setIsProcessingCard(false)
    }
  }

  // Auto-fill test card details for sandbox testing
  const handleFillTestCard = () => {
    setCardNumber('4242 4242 4242 4242')
    setCardHolder(user?.full_name?.toUpperCase() || 'NGUYEN VAN A')
    setCardExpMonth('12')
    setCardExpYear('28')
    setCardCvc('123')
    info('Đã điền thông tin thẻ Visa Test (Sandbox).')
  }

  // Copy to clipboard helper
  const handleCopy = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(fieldName)
    setTimeout(() => setCopiedField(null), 2000)
    success(`Đã sao chép: ${text}`)
  }

  // Format format mm:ss
  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // Filter plans based on sub-toggle
  const filteredPlans = plans.filter((p) => p.type === planTypeTab)

  return (
    <div className="min-h-full pb-16">
      {/* Header */}
      <div className="relative overflow-hidden bg-gradient-to-b from-indigo-50/60 via-white to-transparent dark:from-indigo-950/20 dark:via-transparent dark:to-transparent border-b border-slate-200/80 dark:border-white/[0.08] px-4 sm:px-8 pt-8 pb-10">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100/80 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 text-xs font-semibold mb-3 border border-indigo-200 dark:border-indigo-500/20">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Nâng cấp & Nạp Credit Tự Động</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                Gói Cước & Dịch Vụ AI
              </h1>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed">
                Nạp credit chuyển khoản VietQR tự động quét mã, PayOS hoặc Stripe. Kích hoạt credit
                tức thì trong vòng 5-15 giây.
              </p>
            </div>

            {/* Current user balance card */}
            <div className="bg-white dark:bg-[#12151C] border border-slate-200/80 dark:border-white/[0.08] rounded-2xl p-4 shadow-sm flex items-center gap-4 flex-shrink-0">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-amber-400 to-amber-500 flex items-center justify-center text-white shadow-md shadow-amber-500/20">
                <Zap className="w-6 h-6 fill-current" />
              </div>
              <div>
                <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">
                  Số dư khả dụng
                </span>
                <span className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                  {(user?.credits ?? user?.credit_balance ?? 0).toLocaleString()}{' '}
                  <span className="text-xs font-normal text-slate-500">credit</span>
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs (Plans vs Orders) */}
          <div className="flex items-center gap-2 mt-8 border-b border-slate-200 dark:border-white/[0.08]">
            <button
              onClick={() => handleSwitchTab('plans')}
              className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'plans'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <CreditCard className="w-4 h-4" />
              <span>Bảng Gói Cước</span>
            </button>
            <button
              onClick={() => handleSwitchTab('orders')}
              className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'orders'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Lịch Sử Đơn Hàng & Hóa Đơn</span>
              {ordersTotal > 0 && (
                <span className="px-2 py-0.5 rounded-full text-[11px] bg-slate-100 dark:bg-white/[0.08] text-slate-700 dark:text-slate-300">
                  {ordersTotal}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-8 mt-8">
        {/* ==================== TAB 1: PLANS ==================== */}
        {activeTab === 'plans' && (
          <div>
            {/* Sub-toggle: Gói theo lượt vs Gói tháng */}
            <div className="flex justify-center mb-10">
              <div className="inline-flex items-center p-1 bg-slate-100 dark:bg-[#12151C] rounded-xl border border-slate-200 dark:border-white/[0.08]">
                <button
                  onClick={() => handleSwitchPlanType('credit_pack')}
                  className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    planTypeTab === 'credit_pack'
                      ? 'bg-white dark:bg-indigo-600 text-indigo-600 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  ⚡ Gói nạp theo lượt (Không thời hạn)
                </button>
                <button
                  onClick={() => handleSwitchPlanType('subscription')}
                  className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    planTypeTab === 'subscription'
                      ? 'bg-white dark:bg-indigo-600 text-indigo-600 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  👑 Gói đăng ký tháng (VIP Studio)
                </button>
              </div>
            </div>

            {/* Plans Grid */}
            {isLoadingPlans ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-96 rounded-2xl bg-slate-100 dark:bg-white/[0.04] animate-pulse"
                  />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {filteredPlans.map((plan) => {
                  const isPopular =
                    plan.badge?.includes('Phổ biến') ||
                    plan.code === 'credit_500k' ||
                    plan.code === 'plan_pro'
                  return (
                    <div
                      key={plan.id}
                      className={`relative flex flex-col justify-between rounded-2xl p-6 transition-all duration-200 ${
                        isPopular
                          ? 'border-2 border-indigo-600 dark:border-indigo-500 bg-white dark:bg-[#12151C] shadow-lg shadow-indigo-500/10'
                          : 'border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] hover:border-slate-300 dark:hover:border-white/[0.15]'
                      }`}
                    >
                      {/* Popular / Discount Badge */}
                      {plan.badge && (
                        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                          <span className="px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm">
                            {plan.badge}
                          </span>
                        </div>
                      )}

                      <div>
                        {/* Title & Description */}
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight mt-1">
                          {plan.name}
                        </h3>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 min-h-[32px] leading-relaxed">
                          {plan.description}
                        </p>

                        {/* Price */}
                        <div className="mt-4 pb-4 border-b border-slate-100 dark:border-white/[0.06]">
                          <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                              {plan.price.toLocaleString()}
                            </span>
                            <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                              đ {plan.duration_days > 0 ? '/ tháng' : ''}
                            </span>
                          </div>
                          <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs font-bold">
                            <Zap className="w-3.5 h-3.5 fill-current" />
                            <span>+{plan.credits.toLocaleString()} credits</span>
                          </div>
                        </div>

                        {/* Feature Highlights */}
                        <ul className="mt-6 space-y-3 text-xs text-slate-600 dark:text-slate-300">
                          <li className="flex items-center gap-2.5">
                            <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span>
                              Lưu trữ file âm thanh <strong>{plan.storage_days} ngày</strong>
                            </span>
                          </li>
                          <li className="flex items-center gap-2.5">
                            <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span>
                              Giọng đọc:{' '}
                              <strong>
                                {plan.has_premium_voices
                                  ? 'Toàn bộ giọng Premium'
                                  : 'Giọng Tiêu Chuẩn Edge'}
                              </strong>
                            </span>
                          </li>
                          <li className="flex items-center gap-2.5">
                            <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span>
                              Hàng đợi:{' '}
                              <strong>
                                {plan.queue_priority === 'ultra'
                                  ? 'Siêu tốc (Ultra)'
                                  : plan.queue_priority === 'high'
                                    ? 'Ưu tiên cao'
                                    : 'Tiêu chuẩn'}
                              </strong>
                            </span>
                          </li>
                          <li className="flex items-center gap-2.5">
                            <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span>Tải phụ đề SRT & VTT kèm timestamp</span>
                          </li>
                          {plan.has_api_access && (
                            <li className="flex items-center gap-2.5">
                              <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                              <span>
                                Quyền tích hợp <strong>API & Webhook</strong>
                              </span>
                            </li>
                          )}
                        </ul>
                      </div>

                      {/* CTA Button */}
                      <div className="mt-8">
                        <button
                          type="button"
                          aria-label={plan.price === 0 ? 'Đang Sử Dụng' : 'Nạp Gói Này'}
                          onClick={() => handleSelectPlan(plan)}
                          className={`w-full py-2.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                            isPopular
                              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20'
                              : 'bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-slate-900'
                          }`}
                        >
                          <span>{plan.price === 0 ? 'Đang Sử Dụng' : 'Nạp Gói Này'}</span>
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Feature Comparison Table */}
            <div className="mt-16 bg-white dark:bg-[#12151C] rounded-2xl border border-slate-200 dark:border-white/[0.08] p-6 sm:p-8">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight mb-2">
                Bảng So Sánh Chi Tiết Quyền Lợi
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
                So sánh tính năng giữa các gói cước để chọn giải pháp phù hợp nhất với dự án của
                bạn.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-white/[0.08] text-slate-500 dark:text-slate-400">
                      <th className="py-3 px-4 font-semibold">Tính năng</th>
                      <th className="py-3 px-4 font-semibold">Gói Miễn Phí (Free)</th>
                      <th className="py-3 px-4 font-semibold text-indigo-600 dark:text-indigo-400 font-bold">
                        Gói Pro (Khuyên dùng)
                      </th>
                      <th className="py-3 px-4 font-semibold">Gói Business</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04] text-slate-700 dark:text-slate-300">
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Credit định kỳ</td>
                      <td className="py-3.5 px-4">10,000 credit/tháng</td>
                      <td className="py-3.5 px-4 font-semibold text-indigo-600 dark:text-indigo-400">
                        600,000 credit/tháng
                      </td>
                      <td className="py-3.5 px-4 font-semibold">3,000,000 credit/tháng</td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Thời gian lưu file trên Cloud</td>
                      <td className="py-3.5 px-4">7 ngày</td>
                      <td className="py-3.5 px-4">60 ngày</td>
                      <td className="py-3.5 px-4">365 ngày (1 năm)</td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Giọng đọc Studio Premium</td>
                      <td className="py-3.5 px-4 text-slate-400">Chỉ giọng Edge cơ bản</td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400 font-semibold">
                        ✓ Đầy đủ Azure Neural & Edge
                      </td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400 font-semibold">
                        ✓ Toàn bộ + ElevenLabs Studio
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Xử lý đồng thời (Concurrency)</td>
                      <td className="py-3.5 px-4">1 tác vụ</td>
                      <td className="py-3.5 px-4">3 tác vụ đồng thời</td>
                      <td className="py-3.5 px-4">10 tác vụ đồng thời</td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Ưu tiên hàng đợi</td>
                      <td className="py-3.5 px-4">Tiêu chuẩn</td>
                      <td className="py-3.5 px-4 font-semibold text-indigo-600 dark:text-indigo-400">
                        Ưu tiên cao (High Priority)
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-purple-600 dark:text-purple-400">
                        Siêu tốc không chờ (Ultra)
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">API & Webhook Developers</td>
                      <td className="py-3.5 px-4 text-slate-400">—</td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400 font-semibold">
                        ✓ Khóa API cá nhân
                      </td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400 font-semibold">
                        ✓ Không giới hạn API Rate Limit
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3.5 px-4 font-medium">Tải phụ đề SRT / VTT</td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400">✓ Có</td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400">✓ Có</td>
                      <td className="py-3.5 px-4 text-emerald-600 dark:text-emerald-400">✓ Có</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ==================== TAB 2: ORDERS & INVOICES ==================== */}
        {activeTab === 'orders' && (
          <div className="bg-white dark:bg-[#12151C] rounded-2xl border border-slate-200 dark:border-white/[0.08] p-6 sm:p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                  Lịch Sử Đơn Hàng & Biên Lai
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Xem lại toàn bộ lịch sử thanh toán nạp credit và tải về biên lai PDF hợp lệ.
                </p>
              </div>
              <button
                onClick={() => fetchOrders(ordersPage)}
                className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-all"
                title="Làm mới"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {isLoadingOrders ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-16 rounded-xl bg-slate-100 dark:bg-white/[0.04] animate-pulse"
                  />
                ))}
              </div>
            ) : orders.length === 0 ? (
              <div className="py-16 text-center">
                <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  Chưa có giao dịch thanh toán nào
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Khi bạn nạp credit, hóa đơn sẽ hiển thị tại đây.
                </p>
                <button
                  onClick={() => handleSwitchTab('plans')}
                  className="mt-4 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-all inline-flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Khám phá các gói cước</span>
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-white/[0.08] text-slate-500 dark:text-slate-400">
                      <th className="py-3 px-3 font-semibold">Mã đơn</th>
                      <th className="py-3 px-3 font-semibold">Gói dịch vụ</th>
                      <th className="py-3 px-3 font-semibold">Số tiền</th>
                      <th className="py-3 px-3 font-semibold">Phương thức</th>
                      <th className="py-3 px-3 font-semibold">Trạng thái</th>
                      <th className="py-3 px-3 font-semibold">Thời gian</th>
                      <th className="py-3 px-3 font-semibold text-right">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04] text-slate-700 dark:text-slate-300">
                    {orders.map((order) => (
                      <tr
                        key={order.id}
                        className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02]"
                      >
                        <td className="py-3.5 px-3 font-mono font-bold text-slate-900 dark:text-white">
                          #{order.order_code}
                        </td>
                        <td className="py-3.5 px-3 font-medium">
                          {order.plan_name || 'Nạp Credit'}
                          <span className="block text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                            +{order.credits_to_add.toLocaleString()} credits
                          </span>
                        </td>
                        <td className="py-3.5 px-3 font-bold text-slate-900 dark:text-white">
                          {order.final_amount.toLocaleString()} đ
                          {order.discount_amount > 0 && (
                            <span className="block text-[10px] text-slate-400 line-through">
                              {order.original_amount.toLocaleString()} đ
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-3 uppercase text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                          {order.payment_method}
                        </td>
                        <td className="py-3.5 px-3">
                          {order.status === 'paid' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                              <CheckCircle2 className="w-3 h-3" />
                              Đã thanh toán
                            </span>
                          )}
                          {order.status === 'pending' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
                              <Clock className="w-3 h-3 animate-spin" />
                              Chờ thanh toán
                            </span>
                          )}
                          {order.status === 'cancelled' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 dark:bg-white/[0.06] dark:text-slate-400">
                              Đã hủy
                            </span>
                          )}
                          {order.status === 'failed' && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400">
                              Thất bại
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-3 text-slate-500 dark:text-slate-400 text-[11px]">
                          {new Date(order.created_at).toLocaleString('vi-VN')}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          <div className="inline-flex items-center gap-2">
                            {order.status === 'paid' && (
                              <button
                                onClick={() => handleDownloadReceipt(order)}
                                disabled={isDownloadingPdf}
                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-white/[0.1] transition-all inline-flex items-center gap-1.5"
                                title="Tải biên lai PDF"
                              >
                                <Download className="w-3.5 h-3.5" />
                                <span>Tải PDF</span>
                              </button>
                            )}
                            {order.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => setActiveOrder(order)}
                                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-all inline-flex items-center gap-1"
                                >
                                  <QrCode className="w-3.5 h-3.5" />
                                  <span>Mở QR</span>
                                </button>
                                <button
                                  onClick={() => handleCancelOrder(order.id)}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 transition-all"
                                  title="Hủy đơn"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ==================== MODAL 1: CHECKOUT CONFIGURATION ==================== */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-white dark:bg-[#12151C] rounded-3xl border border-slate-200 dark:border-white/[0.1] shadow-2xl overflow-hidden p-6 sm:p-8">
            {/* Close Button */}
            <button
              onClick={() => setSelectedPlan(null)}
              className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-all"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Thanh Toán Đơn Hàng
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Kiểm tra thông tin gói và lựa chọn phương thức thanh toán thuận tiện.
            </p>

            {/* Selected Plan Summary Box */}
            <div className="mt-5 p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-500/10 border border-indigo-100 dark:border-indigo-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 dark:text-white text-sm block">
                    {selectedPlan.name}
                  </span>
                  <span className="text-xs text-indigo-600 dark:text-indigo-400 font-bold">
                    +{selectedPlan.credits.toLocaleString()} credits
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-base font-extrabold text-slate-900 dark:text-white block">
                    {selectedPlan.price.toLocaleString()} đ
                  </span>
                  {selectedPlan.duration_days > 0 && (
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">
                      / 30 ngày
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Coupon Input */}
            <div className="mt-5">
              <label
                htmlFor={couponInputId}
                className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Mã giảm giá (Coupon)
              </label>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    id={couponInputId}
                    type="text"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                    placeholder="Ví dụ: WELCOME20, VOXIFY50K"
                    className="w-full pl-3.5 pr-8 py-2 rounded-xl text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 uppercase font-mono tracking-wider"
                  />
                  {couponResult?.valid && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 absolute right-2.5 top-1/2 -translate-y-1/2" />
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleValidateCoupon}
                  disabled={isValidatingCoupon || !couponCode.trim()}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 dark:bg-white dark:text-slate-900 text-white hover:bg-slate-800 transition-all disabled:opacity-50"
                >
                  {isValidatingCoupon ? 'Đang kiểm tra...' : 'Áp dụng'}
                </button>
              </div>

              {couponResult && (
                <p
                  className={`text-[11px] mt-1.5 font-medium ${couponResult.valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500'}`}
                >
                  {couponResult.message}
                </p>
              )}
            </div>

            {/* Payment Gateway Selection */}
            <div className="mt-6">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Phương thức thanh toán
              </label>
              <div className="space-y-2">
                <label
                  onClick={() => setPaymentMethod('vietqr')}
                  className={`flex items-center justify-between p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    paymentMethod === 'vietqr'
                      ? 'border-indigo-600 bg-indigo-50/30 dark:bg-indigo-500/10 text-indigo-900 dark:text-white'
                      : 'border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.15]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center flex-shrink-0">
                      <QrCode className="w-5 h-5" />
                    </div>
                    <div>
                      <span className="text-xs font-bold block text-slate-900 dark:text-white">
                        VietQR (Napas 24/7 Tự Động)
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        Quét mã bằng mọi app ngân hàng (MB, VCB, Techcombank, Momo...)
                      </span>
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="payment_method"
                    checked={paymentMethod === 'vietqr'}
                    onChange={() => setPaymentMethod('vietqr')}
                    className="text-indigo-600 focus:ring-indigo-500"
                  />
                </label>

                <label
                  onClick={() => setPaymentMethod('payos')}
                  className={`flex items-center justify-between p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    paymentMethod === 'payos'
                      ? 'border-indigo-600 bg-indigo-50/30 dark:bg-indigo-500/10 text-indigo-900 dark:text-white'
                      : 'border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.15]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center flex-shrink-0">
                      <Zap className="w-5 h-5" />
                    </div>
                    <div>
                      <span className="text-xs font-bold block text-slate-900 dark:text-white">
                        Cổng PayOS
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        Cổng thanh toán tự động VietQR chuẩn bảo mật PCI-DSS
                      </span>
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="payment_method"
                    checked={paymentMethod === 'payos'}
                    onChange={() => setPaymentMethod('payos')}
                    className="text-indigo-600 focus:ring-indigo-500"
                  />
                </label>

                <label
                  onClick={() => setPaymentMethod('stripe')}
                  className={`flex items-center justify-between p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    paymentMethod === 'stripe'
                      ? 'border-indigo-600 bg-indigo-50/30 dark:bg-indigo-500/10 text-indigo-900 dark:text-white'
                      : 'border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.15]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                      <CreditCard className="w-5 h-5" />
                    </div>
                    <div>
                      <span className="text-xs font-bold block text-slate-900 dark:text-white">
                        Thẻ Quốc Tế (Stripe)
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        Visa, Mastercard, JCB, Apple Pay
                      </span>
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="payment_method"
                    checked={paymentMethod === 'stripe'}
                    onChange={() => setPaymentMethod('stripe')}
                    className="text-indigo-600 focus:ring-indigo-500"
                  />
                </label>
              </div>
            </div>

            {/* Total calculation */}
            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/[0.08] flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-500 dark:text-slate-400 block">
                  Tổng tiền thanh toán
                </span>
                {couponResult?.valid && (
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                    Đã giảm: -{couponResult.discount_amount.toLocaleString()} đ
                  </span>
                )}
              </div>
              <div className="text-right">
                <span className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400">
                  {(couponResult?.valid
                    ? couponResult.final_amount
                    : selectedPlan.price
                  ).toLocaleString()}{' '}
                  đ
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSelectedPlan(null)}
                className="flex-1 py-3 px-4 rounded-xl text-xs font-bold border border-slate-200 dark:border-white/[0.1] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-all"
              >
                Đóng
              </button>
              <button
                type="button"
                onClick={handleCreateOrder}
                disabled={isSubmittingOrder}
                className="flex-1 py-3 px-4 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <span>{isSubmittingOrder ? 'Đang tạo đơn...' : 'Tiến Hành Thanh Toán'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== MODAL 2: REALTIME PAYMENT WAITING SCREEN ==================== */}
      {activeOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-xl bg-white dark:bg-[#12151C] rounded-3xl border border-slate-200 dark:border-white/[0.1] shadow-2xl overflow-hidden p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
            {/* Close Button */}
            <button
              onClick={() => setActiveOrder(null)}
              className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-all"
            >
              <X className="w-5 h-5" />
            </button>

            {/* STATUS: PAID */}
            {activeOrder.status === 'paid' ? (
              <div className="py-8 text-center">
                <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center mb-4">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
                <h3 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                  Thanh Toán Thành Công!
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-sm mx-auto">
                  Hệ thống đã nhận được tiền và cộng ngay{' '}
                  <strong>+{activeOrder.credits_to_add.toLocaleString()} credit</strong> vào tài
                  khoản của bạn.
                </p>

                <div className="mt-6 p-4 rounded-2xl bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.08] max-w-sm mx-auto text-left text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Mã đơn hàng:</span>
                    <span className="font-mono font-bold text-slate-900 dark:text-white">
                      #{activeOrder.order_code}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Số tiền:</span>
                    <span className="font-bold text-slate-900 dark:text-white">
                      {activeOrder.final_amount.toLocaleString()} đ
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Thời gian:</span>
                    <span className="text-slate-700 dark:text-slate-300">
                      {activeOrder.paid_at
                        ? new Date(activeOrder.paid_at).toLocaleString('vi-VN')
                        : 'Vừa xong'}
                    </span>
                  </div>
                </div>

                <div className="mt-8 flex items-center justify-center gap-3">
                  <button
                    onClick={() => handleDownloadReceipt(activeOrder)}
                    disabled={isDownloadingPdf}
                    className="py-2.5 px-4 rounded-xl text-xs font-bold border border-slate-200 dark:border-white/[0.1] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-all inline-flex items-center gap-1.5"
                  >
                    <Download className="w-4 h-4" />
                    <span>{isDownloadingPdf ? 'Đang tạo PDF...' : 'Tải Biên Lai (PDF)'}</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveOrder(null)
                      navigate('/studio')
                    }}
                    className="py-2.5 px-5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/25 transition-all inline-flex items-center gap-1.5"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Bắt Đầu Tạo Giọng Nói</span>
                  </button>
                </div>
              </div>
            ) : (
              /* STATUS: PENDING */
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-white/[0.08]">
                  <div>
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 mb-1 border border-amber-200 dark:border-amber-500/20">
                      <Clock className="w-3 h-3 animate-spin" />
                      <span>
                        {activeOrder.payment_method === 'stripe'
                          ? 'Chờ xác nhận thanh toán thẻ'
                          : 'Đang chờ chuyển khoản'}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                      {activeOrder.payment_method === 'stripe'
                        ? 'Thanh Toán Thẻ Quốc Tế (Visa / Mastercard)'
                        : activeOrder.payment_method === 'payos'
                          ? 'Cổng Thanh Toán PayOS (VietQR Tự Động)'
                          : 'Quét Mã VietQR Để Thanh Toán'}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block font-medium">Hết hạn sau</span>
                    <span className="text-sm font-mono font-bold text-amber-600 dark:text-amber-400">
                      {formatCountdown(timeRemaining)}
                    </span>
                  </div>
                </div>

                {/* ===== PHƯƠNG THỨC 1: STRIPE / THẺ TÍN DỤNG QUỐC TẾ ===== */}
                {activeOrder.payment_method === 'stripe' && (
                  <div className="mt-5 space-y-5">
                    {/* Visual Card Preview */}
                    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-tr from-slate-900 via-indigo-950 to-slate-900 text-white p-5 border border-white/15 shadow-xl">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CreditCard className="w-6 h-6 text-indigo-400" />
                          <span className="text-xs font-bold tracking-widest uppercase text-slate-300">
                            VOXIFY CREDIT CARD
                          </span>
                        </div>
                        <span className="font-extrabold italic text-sm text-amber-400 tracking-wider">
                          {cardNumber.startsWith('5') ? 'MASTERCARD' : 'VISA'}
                        </span>
                      </div>

                      {/* Chip */}
                      <div className="my-4 w-10 h-7 rounded bg-gradient-to-tr from-amber-300 to-amber-500 border border-amber-200 shadow-inner" />

                      {/* Card Number */}
                      <div className="font-mono text-lg font-bold tracking-widest text-slate-100">
                        {cardNumber || '•••• •••• •••• ••••'}
                      </div>

                      {/* Cardholder & Expiry */}
                      <div className="mt-4 flex items-center justify-between text-xs">
                        <div>
                          <span className="text-[9px] uppercase tracking-wider text-slate-400 block">
                            Chủ thẻ
                          </span>
                          <span className="font-semibold uppercase tracking-wider text-slate-200">
                            {cardHolder || 'NGUYEN VAN A'}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[9px] uppercase tracking-wider text-slate-400 block">
                            Hết hạn
                          </span>
                          <span className="font-mono font-semibold text-slate-200">
                            {cardExpMonth}/{cardExpYear}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Credit Card Input Form */}
                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Số thẻ (16 chữ số)
                        </label>
                        <input
                          type="text"
                          maxLength={19}
                          value={cardNumber}
                          onChange={(e) => {
                            const v = e.target.value
                              .replace(/\D/g, '')
                              .replace(/(\d{4})/g, '$1 ')
                              .trim()
                            setCardNumber(v)
                          }}
                          placeholder="4242 4242 4242 4242"
                          className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                            Tên in trên thẻ (không dấu)
                          </label>
                          <input
                            type="text"
                            value={cardHolder}
                            onChange={(e) => setCardHolder(e.target.value.toUpperCase())}
                            placeholder="NGUYEN VAN A"
                            className="w-full px-3.5 py-2.5 rounded-xl uppercase font-mono text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                              Hết hạn (MM/YY)
                            </label>
                            <div className="flex items-center gap-1">
                              <input
                                type="text"
                                maxLength={2}
                                value={cardExpMonth}
                                onChange={(e) => setCardExpMonth(e.target.value.replace(/\D/g, ''))}
                                placeholder="12"
                                className="w-1/2 text-center px-2 py-2.5 rounded-xl font-mono text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white"
                              />
                              <span className="text-slate-400">/</span>
                              <input
                                type="text"
                                maxLength={2}
                                value={cardExpYear}
                                onChange={(e) => setCardExpYear(e.target.value.replace(/\D/g, ''))}
                                placeholder="28"
                                className="w-1/2 text-center px-2 py-2.5 rounded-xl font-mono text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                              Mã CVC
                            </label>
                            <input
                              type="password"
                              maxLength={4}
                              value={cardCvc}
                              onChange={(e) => setCardCvc(e.target.value.replace(/\D/g, ''))}
                              placeholder="123"
                              className="w-full text-center px-3 py-2.5 rounded-xl font-mono text-xs bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.1] text-slate-900 dark:text-white"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Quick fill test card */}
                      <div className="flex items-center justify-between pt-1">
                        <button
                          type="button"
                          onClick={handleFillTestCard}
                          className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline font-semibold inline-flex items-center gap-1"
                        >
                          <Zap className="w-3 h-3 fill-current" />
                          <span>⚡ Điền nhanh thẻ Visa Test (Sandbox)</span>
                        </button>
                        <div className="flex items-center gap-1 text-[11px] text-slate-400">
                          <Lock className="w-3 h-3 text-emerald-500" />
                          <span>Bảo mật 256-bit SSL</span>
                        </div>
                      </div>

                      {/* Pay With Card Button */}
                      <button
                        type="button"
                        onClick={handlePayWithCard}
                        disabled={isProcessingCard}
                        className="w-full mt-3 py-3 px-4 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>
                          {isProcessingCard
                            ? 'Đang xử lý qua Stripe...'
                            : `Xác Nhận & Thanh Toán ${activeOrder.final_amount.toLocaleString()} đ`}
                        </span>
                      </button>

                      {/* Optional external link if checkout_url is a Stripe hosted checkout page */}
                      {activeOrder.checkout_url &&
                        activeOrder.checkout_url.startsWith('https://checkout.stripe.com') && (
                          <div className="text-center pt-1">
                            <a
                              href={activeOrder.checkout_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-slate-500 hover:text-indigo-600 underline inline-flex items-center gap-1"
                            >
                              <span>Hoặc thanh toán qua trang chính thức Stripe Checkout</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                    </div>
                  </div>
                )}

                {/* ===== PHƯƠNG THỨC 2 & 3: VIETQR HOẶC PAYOS ===== */}
                {activeOrder.payment_method !== 'stripe' && (
                  <div>
                    {/* QR Code and Bank Details */}
                    <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-6 items-center">
                      {/* QR Image Box */}
                      <div className="flex flex-col items-center justify-center p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
                        {activeOrder.qr_url ? (
                          <img
                            src={activeOrder.qr_url}
                            alt="VietQR Payment Code"
                            className="w-48 h-48 object-contain rounded-lg"
                          />
                        ) : (
                          <div className="w-48 h-48 flex items-center justify-center text-slate-400">
                            <QrCode className="w-16 h-16" />
                          </div>
                        )}
                        <span className="text-[10px] text-slate-500 mt-2 font-medium text-center">
                          {activeOrder.payment_method === 'payos'
                            ? 'Quét mã QR qua app ngân hàng hoặc cổng PayOS'
                            : 'Mở app ngân hàng quét mã QR để điền tự động'}
                        </span>

                        {activeOrder.checkout_url && activeOrder.payment_method === 'payos' && (
                          <a
                            href={activeOrder.checkout_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-3 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-purple-600 text-white hover:bg-purple-700 transition-all inline-flex items-center gap-1.5"
                          >
                            <span>Mở Cổng PayOS</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>

                      {/* Transfer Details with 1-click Copy */}
                      <div className="space-y-3 text-xs">
                        <div>
                          <span className="text-[10px] text-slate-400 block">
                            Số tiền cần chuyển chính xác:
                          </span>
                          <div className="flex items-center justify-between mt-0.5 p-2 rounded-xl bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.08]">
                            <span className="font-mono text-base font-extrabold text-indigo-600 dark:text-indigo-400">
                              {activeOrder.final_amount.toLocaleString()} đ
                            </span>
                            <button
                              onClick={() =>
                                handleCopy(activeOrder.final_amount.toString(), 'amount')
                              }
                              className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-white"
                              title="Sao chép"
                            >
                              {copiedField === 'amount' ? (
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>

                        <div>
                          <span className="text-[10px] text-slate-400 block">
                            Nội dung chuyển khoản (Bắt buộc):
                          </span>
                          <div className="flex items-center justify-between mt-0.5 p-2 rounded-xl bg-amber-50/50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
                            <span className="font-mono font-bold text-amber-700 dark:text-amber-400">
                              {activeOrder.transfer_content || activeOrder.order_code}
                            </span>
                            <button
                              onClick={() =>
                                handleCopy(
                                  activeOrder.transfer_content || activeOrder.order_code,
                                  'content'
                                )
                              }
                              className="p-1 rounded text-amber-600 hover:text-amber-700"
                              title="Sao chép"
                            >
                              {copiedField === 'content' ? (
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>

                        <div>
                          <span className="text-[10px] text-slate-400 block">
                            Số tài khoản & Ngân hàng:
                          </span>
                          <div className="flex items-center justify-between mt-0.5 p-2 rounded-xl bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.08]">
                            <div>
                              <span className="font-mono font-bold text-slate-900 dark:text-white block">
                                {activeOrder.bank_account_no || '0333888999'}
                              </span>
                              <span className="text-[10px] text-slate-500 block">
                                {activeOrder.bank_name || 'MBBank'} -{' '}
                                {activeOrder.bank_account_name || 'VOXIFY AI STUDIO'}
                              </span>
                            </div>
                            <button
                              onClick={() =>
                                handleCopy(activeOrder.bank_account_no || '0333888999', 'acc')
                              }
                              className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-white"
                              title="Sao chép"
                            >
                              {copiedField === 'acc' ? (
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Important notice alert */}
                    <div className="mt-5 p-3 rounded-xl bg-slate-50 dark:bg-[#0B0D12] border border-slate-200 dark:border-white/[0.08] flex items-start gap-2.5 text-xs text-slate-500 dark:text-slate-400">
                      <ShieldCheck className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span>
                        Sau khi bạn chuyển khoản thành công, hệ thống sẽ tự động đối soát và cộng credit
                        trong 5 - 15 giây. Bạn không cần tải lại trang.
                      </span>
                    </div>
                  </div>
                )}

                {/* Simulation Sandbox Button for Demo/Testing & Cancel */}
                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-3">
                  <button
                    onClick={() => handleCancelOrder(activeOrder.id)}
                    className="text-xs text-red-500 hover:text-red-600 font-semibold py-2 px-3 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10 transition-all"
                  >
                    Hủy đơn hàng này
                  </button>

                  <div className="flex items-center gap-2">
                    {/* Sandbox Simulate Payment Button */}
                    <button
                      onClick={handleSimulatePayment}
                      disabled={isSimulatingPayment}
                      className="py-2 px-3.5 rounded-xl text-xs font-bold bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-500/30 transition-all inline-flex items-center gap-1.5"
                      title="Mô phỏng thanh toán thành công tức thì (cho tester/dev)"
                    >
                      <Zap className="w-3.5 h-3.5 fill-current" />
                      <span>
                        {isSimulatingPayment ? 'Đang xử lý...' : 'Mô Phỏng Sandbox (Test Demo)'}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
