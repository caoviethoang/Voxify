import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { apiTrackAffiliateClick } from '../api/affiliate'

const STORAGE_KEY = 'voxify_ref'

export function useAffiliateTracking() {
  const location = useLocation()
  const [referralCode, setReferralCode] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY)
  })

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const refParam = params.get('ref')

    if (refParam && refParam.trim()) {
      const cleanRef = refParam.trim().toUpperCase()
      localStorage.setItem(STORAGE_KEY, cleanRef)
      setReferralCode(cleanRef)

      // Ghi nhận lượt click lên server & lưu cookie 30 ngày
      apiTrackAffiliateClick(cleanRef).catch(err => {
        console.warn('Lỗi khi ghi nhận affiliate tracking click:', err)
      })
    }
  }, [location.search])

  const clearReferralCode = () => {
    localStorage.removeItem(STORAGE_KEY)
    setReferralCode(null)
  }

  return { referralCode, clearReferralCode }
}
