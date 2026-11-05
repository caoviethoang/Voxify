import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCredit } from './useCredit'
import * as creditApi from '../api/credit'

vi.mock('../api/credit', () => ({
  fetchCredits: vi.fn(),
  fetchCreditTransactions: vi.fn(),
  estimateCredits: vi.fn(),
}))

const mockUpdateCredits = vi.fn()
let mockUser: { id: number; email: string; credits: number } | null = null

vi.mock('./useAuth', () => ({
  useAuth: () => ({
    user: mockUser,
    updateCredits: mockUpdateCredits,
  }),
}))

describe('useCredit Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUser = null
  })

  it('returns default balance 0 when user is not logged in', () => {
    const { result } = renderHook(() => useCredit())
    expect(result.current.balance).toBe(0)
    expect(result.current.isLoading).toBe(false)
  })

  it('initializes balance from logged-in user and fetches credits on mount', async () => {
    mockUser = { id: 1, email: 'tester@example.com', credits: 1500 }
    vi.mocked(creditApi.fetchCredits).mockResolvedValueOnce({
      user_id: 1,
      balance: 1800,
      chars_per_credit: 1,
      provider_multipliers: { edge: 1.0, azure: 1.5, elevenlabs: 2.5 },
    })

    const { result } = renderHook(() => useCredit())

    // Initial value is user.credits
    expect(result.current.balance).toBe(1500)

    // Wait for effect to trigger fetchCredits
    await act(async () => {
      await result.current.refreshCredits()
    })

    expect(creditApi.fetchCredits).toHaveBeenCalled()
    expect(mockUpdateCredits).toHaveBeenCalledWith(1800)
  })

  it('calls estimate function from creditApi', async () => {
    vi.mocked(creditApi.estimateCredits).mockResolvedValueOnce({
      char_count: 200,
      provider: 'edge',
      voice: 'vi-VN-HoaiMyNeural',
      multiplier: 1.0,
      estimated_credits: 200,
    })

    const { result } = renderHook(() => useCredit())
    const res = await result.current.estimate({ chars: 200, voice: 'vi-VN-HoaiMyNeural' })
    expect(res.estimated_credits).toBe(200)
    expect(creditApi.estimateCredits).toHaveBeenCalledWith({
      chars: 200,
      voice: 'vi-VN-HoaiMyNeural',
    })
  })

  it('loads transaction history via loadTransactions', async () => {
    const mockTxs = {
      items: [
        {
          id: 1,
          user_id: 1,
          amount: 500,
          type: 'signup_bonus' as const,
          balance_after: 500,
          description: 'Bonus',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 20,
      total_pages: 1,
    }
    vi.mocked(creditApi.fetchCreditTransactions).mockResolvedValueOnce(mockTxs)

    const { result } = renderHook(() => useCredit())

    await act(async () => {
      const data = await result.current.loadTransactions({ page: 1, limit: 10 })
      expect(data).toEqual(mockTxs)
    })

    expect(result.current.historyData).toEqual(mockTxs)
    expect(creditApi.fetchCreditTransactions).toHaveBeenCalledWith({ page: 1, limit: 10 })
  })
})
