import { useState, useCallback, useEffect } from 'react'
import clsx from 'clsx'
import { useAppConfig } from '../hooks/useAppConfig'
import { useVoices } from '../hooks/useVoices'
import { useTTS } from '../hooks/useTTS'
import { useToast } from '../hooks/useToast'
import TextInput from '../components/TextInput'
import VoiceSelector from '../components/VoiceSelector'
import SliderControl from '../components/SliderControl'
import AudioPlayer from '../components/AudioPlayer'
import GenerationHistory from '../components/GenerationHistory'
import ToastContainer from '../components/Toast'
import type { HistoryItem } from '../hooks/useTTS'

export default function TextToSpeech() {
  const { config } = useAppConfig()
  const { data: voiceData, isLoading: voicesLoading } = useVoices()
  const { isLoading, error, currentUrl, history, generate, clearHistory, setError } = useTTS()
  const { toasts, showToast, removeToast } = useToast()

  const [text, setText] = useState('')
  const [selectedVoiceId, setSelectedVoiceId] = useState('')
  const [rate, setRate] = useState(0)
  const [pitch, setPitch] = useState(0)
  const [volume, setVolume] = useState(0)
  const [replayUrl, setReplayUrl] = useState<string | null>(null)
  const [replayVoice, setReplayVoice] = useState('')
  const [replayIsPreview, setReplayIsPreview] = useState(false)

  const voices = voiceData?.voices ?? []

  // Default selected voice from config or first available
  useEffect(() => {
    if (!selectedVoiceId && config.default_voice) {
      setSelectedVoiceId(config.default_voice)
    } else if (!selectedVoiceId && voices.length > 0) {
      setSelectedVoiceId(voices[0].id)
    }
  }, [config.default_voice, voices, selectedVoiceId])

  const selectedVoice = voices.find(v => v.id === selectedVoiceId)
  const selectedVoiceName = selectedVoice?.name ?? selectedVoiceId

  const rateStr = `${rate >= 0 ? '+' : ''}${rate}%`
  const pitchStr = `${pitch >= 0 ? '+' : ''}${pitch}Hz`
  const volumeStr = `${volume >= 0 ? '+' : ''}${volume}%`

  const handleSynthesize = useCallback(async (isPreview: boolean) => {
    if (!text.trim()) {
      showToast('Vui lòng nhập văn bản trước khi tạo giọng nói.', 'error')
      return
    }
    if (!selectedVoiceId) {
      showToast('Vui lòng chọn một giọng đọc trong danh sách.', 'error')
      return
    }
    if (!isPreview && text.length > config.max_chars) {
      showToast(`Văn bản vượt quá giới hạn tối đa ${config.max_chars.toLocaleString('vi-VN')} ký tự.`, 'error')
      return
    }

    setReplayUrl(null)
    const result = await generate({
      text,
      voice: selectedVoiceId,
      rate: rateStr,
      pitch: pitchStr,
      volume: volumeStr,
      preview: isPreview,
      voiceName: selectedVoiceName,
    })

    if (result) {
      showToast(isPreview ? 'Đã tạo nghe thử 200 ký tự đầu thành công!' : 'Đã tạo giọng nói hoàn tất!', 'success')
    }
  }, [text, selectedVoiceId, config.max_chars, generate, rateStr, pitchStr, volumeStr, selectedVoiceName, showToast])

  useEffect(() => {
    if (error) {
      showToast(error, 'error')
      setError(null)
    }
  }, [error, showToast, setError])

  const activeUrl = replayUrl ?? currentUrl
  const activeVoiceName = replayVoice || selectedVoiceName
  const activeIsPreview = replayUrl ? replayIsPreview : (history[0]?.isPreview ?? false)

  const handleDownload = (url: string | null, voiceId: string) => {
    if (!url) {
      showToast('Chưa có bản ghi âm nào để tải về.', 'error')
      return
    }
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const filename = `speech_${voiceId}_${timestamp}.mp3`
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const handleReplay = (item: HistoryItem) => {
    setReplayUrl(item.url)
    setReplayVoice(item.voiceName)
    setReplayIsPreview(item.isPreview)
    showToast('Đang phát lại từ lịch sử phiên.', 'info')
  }

  const resetSliders = () => {
    setRate(0)
    setPitch(0)
    setVolume(0)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Two-column studio layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-5">

        {/* Left column: Text editor + Audio player */}
        <div className="flex flex-col gap-4">
          <TextInput
            value={text}
            onChange={setText}
            maxChars={config.max_chars}
            chunkSize={config.chunk_size}
          />
          <AudioPlayer
            url={activeUrl}
            voiceName={activeVoiceName}
            isPreview={activeIsPreview}
            onDownload={() => handleDownload(activeUrl, selectedVoiceId)}
          />
        </div>

        {/* Right column: Voice + Controls + Actions */}
        <div className="flex flex-col gap-4">
          <VoiceSelector
            voices={voices}
            total={voiceData?.total ?? 0}
            vietnameseCount={voiceData?.vietnamese_count ?? 0}
            selectedId={selectedVoiceId}
            onSelect={setSelectedVoiceId}
            isLoading={voicesLoading}
          />

          {/* Sliders */}
          <div className="bg-[#14141f] rounded-2xl border border-white/5 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Tinh chỉnh âm thanh
              </div>
              <button
                onClick={resetSliders}
                className="text-xs text-white/35 hover:text-brand-400 transition-colors"
              >
                Đặt lại
              </button>
            </div>
            <div className="flex flex-col gap-5">
              <SliderControl
                label="Tốc độ đọc (Speed)"
                value={rate}
                min={-50}
                max={100}
                step={5}
                displayValue={`${(1 + rate / 100).toFixed(2)}x (${rate >= 0 ? '+' : ''}${rate}%)`}
                scaleLabels={['Chậm (0.5x)', 'Chuẩn (1.0x)', 'Nhanh (2.0x)']}
                onChange={setRate}
              />
              <SliderControl
                label="Cao độ (Pitch)"
                value={pitch}
                min={-50}
                max={50}
                step={2}
                displayValue={`${pitch >= 0 ? '+' : ''}${pitch}Hz`}
                scaleLabels={['Trầm (-50Hz)', 'Chuẩn (0Hz)', 'Bổng (+50Hz)']}
                onChange={setPitch}
              />
              <SliderControl
                label="Âm lượng (Volume)"
                value={volume}
                min={-50}
                max={50}
                step={5}
                displayValue={`${volume >= 0 ? '+' : ''}${volume}%`}
                scaleLabels={['Nhỏ (-50%)', 'Chuẩn (0%)', 'Lớn (+50%)']}
                onChange={setVolume}
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={() => handleSynthesize(true)}
              disabled={isLoading}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium border transition-all',
                'border-white/10 bg-white/5 text-white/70 hover:bg-white/10 hover:text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {isLoading ? 'Đang xử lý...' : 'Nghe thử (200 ký tự)'}
            </button>
            <button
              onClick={() => handleSynthesize(false)}
              disabled={isLoading}
              className={clsx(
                'flex-[2] flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all',
                'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/25',
                'disabled:opacity-60 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Đang xử lý...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
                  </svg>
                  Tạo giọng nói
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Session history */}
      <GenerationHistory
        history={history}
        onReplay={handleReplay}
        onDownload={item => handleDownload(item.url, item.voiceId)}
        onClear={clearHistory}
      />

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
