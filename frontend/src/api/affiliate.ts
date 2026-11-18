import client from './client'

export interface AffiliateStats {
  total_clicks: number
  total_signups: number
  total_orders: number
  pending_commission: number
  available_commission: number
  withdrawn_commission: number
  total_earned_commission: number
}

export interface AffiliateCommissionItem {
  id: number
  order_code: string
  buyer_masked_email: string
  order_amount: number
  commission_rate: number
  amount: number
  status: 'pending' | 'approved' | 'cancelled'
  hold_until: string
  created_at: string
}

export interface AffiliateWithdrawalItem {
  id: number
  amount: number
  bank_name: string
  bank_account_number: string
  bank_account_holder: string
  status: 'pending' | 'approved' | 'rejected'
  note?: string | null
  created_at: string
  updated_at?: string | null
}

export interface AffiliateDashboardResponse {
  referral_code: string
  referral_link: string
  commission_rate: number
  hold_period_days: number
  min_payout_amount: number
  stats: AffiliateStats
  commissions: AffiliateCommissionItem[]
  withdrawals: AffiliateWithdrawalItem[]
}

export interface WithdrawalRequestPayload {
  amount: number
  bank_name: string
  bank_account_number: string
  bank_account_holder: string
}

export interface TrackAffiliateResponse {
  success: boolean
  referral_code: string
  message: string
}

export interface CustomizeCodeResponse {
  success: boolean
  referral_code: string
  referral_link: string
  message: string
}

export async function apiGetAffiliateDashboard(): Promise<AffiliateDashboardResponse> {
  const { data } = await client.get<AffiliateDashboardResponse>('/affiliate/dashboard')
  return data
}

export async function apiTrackAffiliateClick(ref: string): Promise<TrackAffiliateResponse> {
  const { data } = await client.post<TrackAffiliateResponse>(`/affiliate/track?ref=${encodeURIComponent(ref)}`)
  return data
}

export async function apiRequestWithdrawal(payload: WithdrawalRequestPayload): Promise<AffiliateWithdrawalItem> {
  const { data } = await client.post<AffiliateWithdrawalItem>('/affiliate/withdraw', payload)
  return data
}

export async function apiCustomizeReferralCode(referral_code: string): Promise<CustomizeCodeResponse> {
  const { data } = await client.put<CustomizeCodeResponse>('/affiliate/code', { referral_code })
  return data
}

export async function apiGetCommissions(page = 1, limit = 20): Promise<AffiliateCommissionItem[]> {
  const { data } = await client.get<AffiliateCommissionItem[]>('/affiliate/commissions', {
    params: { page, limit },
  })
  return data
}

export async function apiGetWithdrawals(page = 1, limit = 20): Promise<AffiliateWithdrawalItem[]> {
  const { data } = await client.get<AffiliateWithdrawalItem[]>('/affiliate/withdrawals', {
    params: { page, limit },
  })
  return data
}
