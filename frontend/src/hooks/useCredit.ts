import { useState, useEffect, useCallback } from 'react'
import {
  fetchCredits,
  fetchCreditTransactions,
  estimateCredits,
  type CreditBalanceResponse,
  type CreditTransactionsResponse,
} from '../api/credit'
import { useAuth } from './useAuth'

export function useCredit() {
  const { user, updateCredits } = useAuth()
  const [data, setData] = useState<CreditBalanceResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [historyData, setHistoryData] = useState<CreditTransactionsResponse | null>(null)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)

  const refreshCredits = useCallback(async () => {
    if (!user) return
    setIsLoading(true)
    try {
      const res = await fetchCredits()
      setData(res)
      updateCredits(res.balance)
      return res.balance
    } catch {
      // Bỏ qua lỗi mạng
    } finally {
      setIsLoading(false)
    }
  }, [user, updateCredits])

  const loadTransactions = useCallback(
    async (params?: { page?: number; limit?: number; type?: string }) => {
      setIsHistoryLoading(true)
      try {
        const res = await fetchCreditTransactions(params)
        setHistoryData(res)
        return res
      } finally {
        setIsHistoryLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    if (user) {
      refreshCredits()
    }
  }, [user, refreshCredits])

  return {
    balance: user?.credits ?? data?.balance ?? 0,
    charsPerCredit: data?.chars_per_credit ?? 1,
    providerMultipliers: data?.provider_multipliers ?? { edge: 1.0 },
    isLoading,
    refreshCredits,
    historyData,
    isHistoryLoading,
    loadTransactions,
    estimate: estimateCredits,
  }
}
