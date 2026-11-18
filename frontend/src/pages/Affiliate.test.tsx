import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Affiliate from './Affiliate'
import * as affiliateApi from '../api/affiliate'
import { ToastProvider } from '../context/ToastContext'

vi.mock('../api/affiliate', () => ({
  apiGetAffiliateDashboard: vi.fn(),
  apiRequestWithdrawal: vi.fn(),
  apiCustomizeReferralCode: vi.fn(),
  apiTrackAffiliateClick: vi.fn(),
}))

const mockDashboardData: affiliateApi.AffiliateDashboardResponse = {
  referral_code: 'VOXTEST99',
  referral_link: 'http://localhost:5173/register?ref=VOXTEST99',
  commission_rate: 0.25,
  hold_period_days: 14,
  min_payout_amount: 200000,
  stats: {
    total_clicks: 142,
    total_signups: 28,
    total_orders: 12,
    pending_commission: 150000,
    available_commission: 500000,
    withdrawn_commission: 300000,
    total_earned_commission: 800000,
  },
  commissions: [
    {
      id: 1,
      order_code: 'ORD_AFF_001',
      buyer_masked_email: 'b***r@gmail.com',
      order_amount: 1000000,
      commission_rate: 0.25,
      amount: 250000,
      status: 'approved',
      hold_until: '2026-11-20T00:00:00Z',
      created_at: '2026-11-06T00:00:00Z',
    },
    {
      id: 2,
      order_code: 'ORD_AFF_002',
      buyer_masked_email: 'u***1@yahoo.com',
      order_amount: 600000,
      commission_rate: 0.25,
      amount: 150000,
      status: 'pending',
      hold_until: '2026-11-25T00:00:00Z',
      created_at: '2026-11-11T00:00:00Z',
    },
  ],
  withdrawals: [
    {
      id: 10,
      amount: 300000,
      bank_name: 'MBBank (Quân Đội)',
      bank_account_number: '0333888999',
      bank_account_holder: 'TRAN VAN A',
      status: 'approved',
      note: 'Đã chi trả thành công',
      created_at: '2026-11-08T00:00:00Z',
    },
  ],
}

describe('Affiliate Program Page Component (Issue #14)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(affiliateApi.apiGetAffiliateDashboard).mockResolvedValue(mockDashboardData)
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    })
  })

  it('renders affiliate program header, 25% commission rate, stats, and referral link', async () => {
    render(
      <ToastProvider>
        <Affiliate />
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/25% Hoa Hồng Trọn Đời/i)).toBeInTheDocument()
    })

    // Referral link & code
    expect(screen.getByDisplayValue('http://localhost:5173/register?ref=VOXTEST99')).toBeInTheDocument()
    expect(screen.getByText('VOXTEST99')).toBeInTheDocument()

    // Key stats
    expect(screen.getByText('142')).toBeInTheDocument() // Clicks
    expect(screen.getByText('28')).toBeInTheDocument() // Signups
    expect(screen.getByText('12')).toBeInTheDocument() // Orders

    // Commission items
    expect(screen.getByText('ORD_AFF_001')).toBeInTheDocument()
    expect(screen.getByText('b***r@gmail.com')).toBeInTheDocument()
    expect(screen.getByText('ORD_AFF_002')).toBeInTheDocument()
    expect(screen.getByText('u***1@yahoo.com')).toBeInTheDocument()
  })

  it('copies referral link to clipboard when clicking copy button', async () => {
    render(
      <ToastProvider>
        <Affiliate />
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Sao chép link/i)).toBeInTheDocument()
    })

    const copyBtn = screen.getByRole('button', { name: /Sao chép link/i })
    fireEvent.click(copyBtn)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('http://localhost:5173/register?ref=VOXTEST99')
  })

  it('switches between commissions tab and withdrawals tab', async () => {
    render(
      <ToastProvider>
        <Affiliate />
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Lịch sử hoa hồng/i)).toBeInTheDocument()
    })

    const withdrawTabBtn = screen.getByRole('button', { name: /Lịch sử rút tiền/i })
    fireEvent.click(withdrawTabBtn)

    // Withdrawal details should be visible
    expect(screen.getByText('#W-10')).toBeInTheDocument()
    expect(screen.getByText('MBBank (Quân Đội)')).toBeInTheDocument()
    expect(screen.getByText('0333888999')).toBeInTheDocument()
    expect(screen.getByText('TRAN VAN A')).toBeInTheDocument()
    expect(screen.getByText('Đã chi trả thành công')).toBeInTheDocument()
  })

  it('opens withdrawal modal and submits a valid payout request', async () => {
    vi.mocked(affiliateApi.apiRequestWithdrawal).mockResolvedValue({
      id: 11,
      amount: 400000,
      bank_name: 'Vietcombank (Ngoại Thương)',
      bank_account_number: '1234567890',
      bank_account_holder: 'TRAN VAN A',
      status: 'pending',
      created_at: '2026-11-18T00:00:00Z',
    })

    render(
      <ToastProvider>
        <Affiliate />
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Yêu cầu rút tiền về tài khoản/i })).toBeInTheDocument()
    })

    const withdrawBtn = screen.getByRole('button', { name: /Yêu cầu rút tiền về tài khoản/i })
    fireEvent.click(withdrawBtn)

    expect(screen.getByText(/Rút tiền hoa hồng Affiliate/i)).toBeInTheDocument()

    // Fill form
    const accountNoInput = screen.getByPlaceholderText(/Ví dụ: 0333888999/i)
    const holderInput = screen.getByPlaceholderText(/NGUYEN VAN A/i)

    fireEvent.change(accountNoInput, { target: { value: '1234567890' } })
    fireEvent.change(holderInput, { target: { value: 'TRAN VAN A' } })

    const confirmBtn = screen.getByRole('button', { name: /Xác nhận rút tiền/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(affiliateApi.apiRequestWithdrawal).toHaveBeenCalledWith(
        expect.objectContaining({
          amount: 500000,
          bank_account_number: '1234567890',
          bank_account_holder: 'TRAN VAN A',
        })
      )
    })
  })

  it('opens customize code modal and submits new referral code', async () => {
    vi.mocked(affiliateApi.apiCustomizeReferralCode).mockResolvedValue({
      success: true,
      referral_code: 'NEWCODE2026',
      referral_link: 'http://localhost:5173/register?ref=NEWCODE2026',
      message: 'Cập nhật mã giới thiệu thành công',
    })

    render(
      <ToastProvider>
        <Affiliate />
      </ToastProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Đổi mã/i)).toBeInTheDocument()
    })

    const editBtn = screen.getByRole('button', { name: /Đổi mã/i })
    fireEvent.click(editBtn)

    expect(screen.getByText(/Tùy chỉnh mã giới thiệu/i)).toBeInTheDocument()

    const codeInput = screen.getByPlaceholderText(/Ví dụ: MYBRAND2026/i)
    fireEvent.change(codeInput, { target: { value: 'NEWCODE2026' } })

    const saveBtn = screen.getByRole('button', { name: /Lưu mã mới/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(affiliateApi.apiCustomizeReferralCode).toHaveBeenCalledWith('NEWCODE2026')
    })
  })
})
