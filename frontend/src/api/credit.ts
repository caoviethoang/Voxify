import client from './client'

export interface CreditBalanceResponse {
  user_id: number
  balance: number
  chars_per_credit: number
  provider_multipliers: Record<string, number>
}

export type CreditTransactionType =
  | 'signup_bonus'
  | 'purchase'
  | 'usage'
  | 'refund'
  | 'admin_adjust'
  | 'affiliate'

export interface CreditTransaction {
  id: number
  user_id: number
  amount: number
  type: CreditTransactionType
  ref_id?: string
  balance_after: number
  description?: string
  created_at: string
}

export interface CreditTransactionsResponse {
  items: CreditTransaction[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface CreditEstimateResponse {
  char_count: number
  provider: string
  voice?: string
  multiplier: number
  estimated_credits: number
}

/**
 * Lấy số dư credit hiện tại của tài khoản
 */
export async function fetchCredits(): Promise<CreditBalanceResponse> {
  const { data } = await client.get<CreditBalanceResponse>('/credits')
  return data
}

/**
 * Lấy danh sách lịch sử biến động sổ cái credit (có phân trang)
 */
export async function fetchCreditTransactions(params?: {
  page?: number
  limit?: number
  type?: string
}): Promise<CreditTransactionsResponse> {
  const { data } = await client.get<CreditTransactionsResponse>('/credits/transactions', {
    params,
  })
  return data
}

/**
 * Ước tính số credit cần dùng theo số ký tự
 */
export async function estimateCredits(params: {
  chars: number
  provider?: string
  voice?: string
}): Promise<CreditEstimateResponse> {
  const { data } = await client.get<CreditEstimateResponse>('/credits/estimate', {
    params,
  })
  return data
}
