import client from './client'

export interface PricingPlan {
  id: number
  code: string
  name: string
  type: 'credit_pack' | 'subscription'
  price: number
  currency: string
  credits: number
  duration_days: number
  storage_days: number
  has_premium_voices: boolean
  has_api_access: boolean
  queue_priority: 'standard' | 'high' | 'ultra'
  concurrency_limit: number
  badge: string | null
  description: string | null
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CouponValidateResult {
  valid: boolean
  code: string
  discount_type: 'percent' | 'fixed' | 'none'
  discount_value: number
  discount_amount: number
  final_amount: number
  message: string
}

export interface Order {
  id: number
  order_code: string
  order_number: number
  user_id: number
  plan_id: number | null
  plan_name: string | null
  plan_code: string | null
  original_amount: number
  discount_amount: number
  final_amount: number
  credits_to_add: number
  payment_method: 'vietqr' | 'payos' | 'stripe'
  status: 'pending' | 'paid' | 'expired' | 'failed' | 'cancelled'
  qr_url: string | null
  checkout_url: string | null
  transfer_content: string | null
  bank_name: string | null
  bank_account_no: string | null
  bank_account_name: string | null
  expires_at: string
  paid_at: string | null
  created_at: string
}

export interface OrderListResponse {
  orders: Order[]
  total: number
  page: number
  limit: number
}

// 1. Lấy danh sách gói cước
export const apiGetPlans = async (): Promise<PricingPlan[]> => {
  const { data } = await client.get<PricingPlan[]>('/payments/plans')
  return data
}

// 2. Kiểm tra mã giảm giá
export const apiValidateCoupon = async (
  code: string,
  order_amount: number
): Promise<CouponValidateResult> => {
  const { data } = await client.post<CouponValidateResult>('/payments/coupons/validate', {
    code,
    order_amount,
  })
  return data
}

// 3. Tạo đơn hàng thanh toán
export const apiCreateOrder = async (params: {
  plan_id: number
  payment_method: string
  coupon_code?: string
}): Promise<Order> => {
  const { data } = await client.post<Order>('/payments/orders', params)
  return data
}

// 4. Lấy chi tiết & trạng thái realtime của đơn hàng
export const apiGetOrder = async (orderId: string | number): Promise<Order> => {
  const { data } = await client.get<Order>(`/payments/orders/${orderId}`)
  return data
}

// 5. Danh sách đơn hàng cá nhân
export const apiGetMyOrders = async (
  page = 1,
  limit = 15
): Promise<{ orders: Order[]; total: number; page: number; limit: number }> => {
  const { data } = await client.get<{
    orders: Order[]
    total: number
    page: number
    limit: number
  }>('/payments/orders', { params: { page, limit } })
  return data
}

// 6. Hủy đơn hàng đang chờ
export const apiCancelOrder = async (orderId: number): Promise<Order> => {
  const { data } = await client.post<Order>(`/payments/orders/${orderId}/cancel`)
  return data
}

// 7. Tải biên lai PDF
export const apiDownloadReceipt = async (
  orderId: string | number,
  orderCode: string
): Promise<void> => {
  const response = await client.get(`/payments/orders/${orderId}/receipt`, {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `voxify-receipt-${orderCode}.pdf`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// 8. Mô phỏng thanh toán Sandbox (dành cho kiểm thử)
export const apiSimulateSandboxPayment = async (
  orderId: number
): Promise<{ success: boolean; already_processed: boolean; order: Order }> => {
  const { data } = await client.post<{
    success: boolean
    already_processed: boolean
    order: Order
  }>('/payments/sandbox/simulate-payment', { order_id: orderId })
  return data
}
