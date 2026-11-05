import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Pricing from './Pricing'
import * as paymentApi from '../api/payment'

vi.mock('../api/payment', () => ({
  apiGetPlans: vi.fn(),
  apiValidateCoupon: vi.fn(),
  apiCreateOrder: vi.fn(),
  apiGetOrder: vi.fn(),
  apiGetMyOrders: vi.fn(),
  apiCancelOrder: vi.fn(),
  apiDownloadReceipt: vi.fn(),
  apiSimulateSandboxPayment: vi.fn(),
  apiPayWithCard: vi.fn(),
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      full_name: 'Tester',
      email: 'tester@voxify.app',
      credits: 15000,
      credit_balance: 15000,
    },
    refreshUser: vi.fn(),
  }),
}))

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
}

vi.mock('../context/ToastContext', () => ({
  useToast: () => mockToast,
}))

const mockPlans: paymentApi.PricingPlan[] = [
  {
    id: 1,
    code: 'credit_100k',
    name: 'Gói 100K Ký Tự',
    type: 'credit_pack',
    price: 59000,
    currency: 'VND',
    credits: 100000,
    duration_days: 0,
    storage_days: 14,
    has_premium_voices: true,
    has_api_access: false,
    queue_priority: 'standard',
    concurrency_limit: 1,
    badge: null,
    description: 'Phù hợp video ngắn',
    display_order: 1,
    is_active: true,
    created_at: '2026-11-05T00:00:00Z',
    updated_at: '2026-11-05T00:00:00Z',
  },
  {
    id: 2,
    code: 'credit_500k',
    name: 'Gói 500K Ký Tự',
    type: 'credit_pack',
    price: 249000,
    currency: 'VND',
    credits: 500000,
    duration_days: 0,
    storage_days: 30,
    has_premium_voices: true,
    has_api_access: true,
    queue_priority: 'high',
    concurrency_limit: 3,
    badge: 'Phổ biến nhất',
    description: 'Tối ưu cho sáng tạo nội dung',
    display_order: 2,
    is_active: true,
    created_at: '2026-11-05T00:00:00Z',
    updated_at: '2026-11-05T00:00:00Z',
  },
  {
    id: 3,
    code: 'plan_pro',
    name: 'Gói Pro Hàng Tháng',
    type: 'subscription',
    price: 199000,
    currency: 'VND',
    credits: 600000,
    duration_days: 30,
    storage_days: 60,
    has_premium_voices: true,
    has_api_access: true,
    queue_priority: 'high',
    concurrency_limit: 3,
    badge: 'Khuyên dùng',
    description: 'Đầy đủ giọng cao cấp',
    display_order: 3,
    is_active: true,
    created_at: '2026-11-05T00:00:00Z',
    updated_at: '2026-11-05T00:00:00Z',
  },
]

describe('Pricing Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(paymentApi.apiGetPlans).mockResolvedValue(mockPlans)
    vi.mocked(paymentApi.apiGetMyOrders).mockResolvedValue({
      orders: [],
      total: 0,
      page: 1,
      limit: 10,
    })
  })

  it('renders plan list and user credit balance correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Pricing />
      </MemoryRouter>
    )

    expect(screen.getByText('Gói Cước & Dịch Vụ AI')).toBeInTheDocument()
    expect(screen.getByText('15,000')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Gói 100K Ký Tự')).toBeInTheDocument()
      expect(screen.getByText('Gói 500K Ký Tự')).toBeInTheDocument()
      expect(screen.getByText('Phổ biến nhất')).toBeInTheDocument()
    })
  })

  it('opens checkout modal and allows applying coupon', async () => {
    vi.mocked(paymentApi.apiValidateCoupon).mockResolvedValue({
      valid: true,
      code: 'WELCOME20',
      discount_type: 'percent',
      discount_value: 20,
      discount_amount: 11800,
      final_amount: 47200,
      message: 'Áp dụng mã giảm giá thành công!',
    })

    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Pricing />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Gói 100K Ký Tự')).toBeInTheDocument()
    })

    const selectButtons = screen.getAllByRole('button', { name: 'Nạp Gói Này' })
    await userEvent.click(selectButtons[0])

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText('Thanh Toán Đơn Hàng')).toBeInTheDocument()
      expect(screen.getByText('VietQR (Napas 24/7 Tự Động)')).toBeInTheDocument()
    })

    // Type coupon
    const couponInput = screen.getByPlaceholderText(/Ví dụ: WELCOME20/i)
    await userEvent.type(couponInput, 'WELCOME20')

    const applyButton = screen.getByRole('button', { name: /Áp dụng/i })
    await userEvent.click(applyButton)

    await waitFor(() => {
      expect(paymentApi.apiValidateCoupon).toHaveBeenCalledWith('WELCOME20', 59000)
      expect(screen.getByText('Áp dụng mã giảm giá thành công!')).toBeInTheDocument()
      expect(screen.getByText(/47,200 đ/i)).toBeInTheDocument()
    })
  })

  it('creates an order and renders realtime payment waiting screen with VietQR', async () => {
    const mockOrder: paymentApi.Order = {
      id: 99,
      order_code: 'VOX99999',
      order_number: 99999,
      user_id: 1,
      plan_id: 1,
      plan_name: 'Gói 100K Ký Tự',
      plan_code: 'credit_100k',
      original_amount: 59000,
      discount_amount: 0,
      final_amount: 59000,
      credits_to_add: 100000,
      payment_method: 'vietqr',
      status: 'pending',
      qr_url: 'https://img.vietqr.io/image/MB-0333888999-compact2.png',
      checkout_url: null,
      transfer_content: 'VOX99999',
      bank_name: 'MBBank',
      bank_account_no: '0333888999',
      bank_account_name: 'VOXIFY AI STUDIO',
      expires_at: new Date(Date.now() + 1800000).toISOString(),
      paid_at: null,
      created_at: new Date().toISOString(),
    }

    vi.mocked(paymentApi.apiCreateOrder).mockResolvedValue(mockOrder)

    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Pricing />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Gói 100K Ký Tự')).toBeInTheDocument()
    })

    const selectButtons = screen.getAllByRole('button', { name: 'Nạp Gói Này' })
    await userEvent.click(selectButtons[0])

    const submitButton = await screen.findByRole('button', { name: /Tiến Hành Thanh Toán/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(paymentApi.apiCreateOrder).toHaveBeenCalled()
      expect(screen.getByText('Quét Mã VietQR Để Thanh Toán')).toBeInTheDocument()
      expect(screen.getByText('VOX99999')).toBeInTheDocument()
      expect(screen.getByText('0333888999')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Mô Phỏng Sandbox/i })).toBeInTheDocument()
    })
  })

  it('creates an order with Stripe and pays successfully using credit card', async () => {
    const mockStripeOrder: paymentApi.Order = {
      id: 100,
      order_code: 'VOX100000',
      order_number: 100000,
      user_id: 1,
      plan_id: 1,
      plan_name: 'Gói 100K Ký Tự',
      plan_code: 'credit_100k',
      original_amount: 59000,
      discount_amount: 0,
      final_amount: 59000,
      credits_to_add: 100000,
      payment_method: 'stripe',
      status: 'pending',
      qr_url: null,
      checkout_url: null,
      transfer_content: 'VOX100000',
      bank_name: null,
      bank_account_no: null,
      bank_account_name: null,
      expires_at: new Date(Date.now() + 1800000).toISOString(),
      paid_at: null,
      created_at: new Date().toISOString(),
    }

    const mockPaidOrder: paymentApi.Order = {
      ...mockStripeOrder,
      status: 'paid',
      paid_at: new Date().toISOString(),
    }

    vi.mocked(paymentApi.apiCreateOrder).mockResolvedValue(mockStripeOrder)
    vi.mocked(paymentApi.apiPayWithCard).mockResolvedValue(mockPaidOrder)

    render(
      <MemoryRouter initialEntries={['/pricing']}>
        <Pricing />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Gói 100K Ký Tự')).toBeInTheDocument()
    })

    const selectButtons = screen.getAllByRole('button', { name: 'Nạp Gói Này' })
    await userEvent.click(selectButtons[0])

    // Select Stripe payment method
    const stripeOption = await screen.findByText('Thẻ Quốc Tế (Stripe)')
    await userEvent.click(stripeOption)

    // Submit order creation
    const submitButton = await screen.findByRole('button', { name: /Tiến Hành Thanh Toán/i })
    await userEvent.click(submitButton)

    // Should display Stripe card payment screen
    await waitFor(() => {
      expect(paymentApi.apiCreateOrder).toHaveBeenCalledWith({
        plan_id: 1,
        payment_method: 'stripe',
        coupon_code: undefined,
      })
      expect(
        screen.getByText('Thanh Toán Thẻ Quốc Tế (Visa / Mastercard)')
      ).toBeInTheDocument()
      expect(screen.getByText(/Điền nhanh thẻ Visa Test/i)).toBeInTheDocument()
    })

    // Click auto-fill test card
    const fillTestCardBtn = screen.getByText(/Điền nhanh thẻ Visa Test/i)
    await userEvent.click(fillTestCardBtn)

    // Click Pay button
    const payBtn = screen.getByRole('button', { name: /Xác Nhận & Thanh Toán/i })
    await userEvent.click(payBtn)

    await waitFor(() => {
      expect(paymentApi.apiPayWithCard).toHaveBeenCalledWith(100, {
        card_number: '4242424242424242',
        cardholder_name: 'TESTER',
        exp_month: '12',
        exp_year: '28',
        cvc: '123',
      })
      expect(screen.getByText(/Thanh toán thành công/i)).toBeInTheDocument()
    })
  })
})
