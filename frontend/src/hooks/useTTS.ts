import { useState, useCallback } from 'react'
import { synthesize, type SynthesizeParams } from '../api/tts'

export interface HistoryItem {
  id: string
  text: string
  voiceId: string
  voiceName: string
  rate: string
  pitch: string
  volume: string
  isPreview: boolean
  blob: Blob
  url: string
  timestamp: Date
}

export function useTTS() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentUrl, setCurrentUrl] = useState<string | null>(null)
  const [currentBlob, setCurrentBlob] = useState<Blob | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])

  const generate = useCallback(async (params: SynthesizeParams & { voiceName: string }) => {
    setIsLoading(true)
    setError(null)
    try {
      const blob = await synthesize(params)
      const url = URL.createObjectURL(blob)

      setCurrentBlob(blob)
      setCurrentUrl(url)

      const item: HistoryItem = {
        id: Date.now().toString(),
        text: params.text,
        voiceId: params.voice,
        voiceName: params.voiceName,
        rate: params.rate,
        pitch: params.pitch,
        volume: params.volume,
        isPreview: params.preview ?? false,
        blob,
        url,
        timestamp: new Date(),
      }
      setHistory(prev => [item, ...prev])
      return { url, blob }
    } catch (err: unknown) {
      let msg = 'Có lỗi xảy ra khi tạo giọng nói.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string; error?: { message?: string } } } }
        msg =
          axiosErr.response?.data?.detail ||
          axiosErr.response?.data?.error?.message ||
          msg
      } else if (err instanceof Error) {
        msg = err.message
      }
      setError(msg)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearHistory = useCallback(() => {
    history.forEach(item => {
      if (item.url !== currentUrl) URL.revokeObjectURL(item.url)
    })
    setHistory([])
  }, [history, currentUrl])

  return { isLoading, error, currentUrl, currentBlob, history, generate, clearHistory, setError }
}
