import { useState, useRef, useEffect } from 'react'
import {
  X,
  Mic,
  Square,
  Play,
  Pause,
  Upload,
  Sparkles,
  ShieldCheck,
  Coins,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { createVoiceClone, getVoiceCloneLimits, type VoiceCloneQuota, type ClonedVoice } from '../../api/voice_clone'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'

interface VoiceCloneModalProps {
  isOpen: boolean
  onClose: () => void
  onVoiceCreated?: (voice: ClonedVoice) => void
}

export default function VoiceCloneModal({ isOpen, onClose, onVoiceCreated }: VoiceCloneModalProps) {
  const { user, refreshUser } = useAuth()
  const toast = useToast()

  const [mode, setMode] = useState<'record' | 'upload'>('record')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [gender, setGender] = useState<'male' | 'female' | 'unspecified'>('male')
  const [consentAccepted, setConsentAccepted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)

  // Uploaded file state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  // Quota & Fee
  const [quota, setQuota] = useState<VoiceCloneQuota | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const timerRef = useRef<number | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Tải thông tin quota & chi phí
  useEffect(() => {
    if (isOpen) {
      getVoiceCloneLimits()
        .then((data) => setQuota(data))
        .catch(() => {})
    } else {
      // Reset state khi đóng
      stopRecording()
      setAudioBlob(null)
      if (audioUrl) URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
      setUploadedFile(null)
      setName('')
      setDescription('')
      setConsentAccepted(false)
    }
  }, [isOpen])

  // Dọn dẹp audio player
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [audioUrl])

  // Bắt đầu thu âm trực tiếp
  const startRecording = async () => {
    try {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
        setAudioUrl(null)
      }
      setAudioBlob(null)
      audioChunksRef.current = []
      setRecordingSeconds(0)

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)
      }

      recorder.start(100)
      setIsRecording(true)

      // Bộ đếm thời gian từ 0s tới tối đa 30s
      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 29) {
            stopRecording()
            return 30
          }
          return prev + 1
        })
      }, 1000)
    } catch (err) {
      console.error('Lỗi truy cập micro:', err)
      toast.error('Không thể truy cập microphone. Vui lòng cấp quyền micro trên trình duyệt.')
    }
  }

  // Dừng thu âm
  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
  }

  // Toggle phát nghe lại mẫu âm thanh
  const togglePlayAudio = () => {
    if (!audioPlayerRef.current && audioUrl) {
      const audio = new Audio(audioUrl)
      audio.onended = () => setIsPlayingAudio(false)
      audioPlayerRef.current = audio
    }

    if (audioPlayerRef.current) {
      if (isPlayingAudio) {
        audioPlayerRef.current.pause()
        setIsPlayingAudio(false)
      } else {
        audioPlayerRef.current.play()
        setIsPlayingAudio(true)
      }
    }
  }

  // Xử lý chọn file tải lên
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 25 * 1024 * 1024) {
      toast.error('Dung lượng tệp không được vượt quá 25MB.')
      return
    }

    setUploadedFile(file)
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    const url = URL.createObjectURL(file)
    setAudioUrl(url)
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current = null
    }
    setIsPlayingAudio(false)
  }

  // Submit tạo voice clone
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      toast.error('Vui lòng nhập tên cho giọng đọc clone.')
      return
    }

    if (!consentAccepted) {
      toast.error('Bạn phải tích xác nhận cam kết chủ quyền giọng nói để tiếp tục.')
      return
    }

    let fileToUpload: File | null = null
    if (mode === 'record') {
      if (!audioBlob || recordingSeconds < 5) {
        toast.error('Mẫu thu âm phải có thời lượng từ 5 đến 30 giây.')
        return
      }
      fileToUpload = new File([audioBlob], `${name.trim()}_sample.webm`, { type: 'audio/webm' })
    } else {
      if (!uploadedFile) {
        toast.error('Vui lòng chọn tệp âm thanh mẫu từ 5 đến 30 giây.')
        return
      }
      fileToUpload = uploadedFile
    }

    const currentBalance = user?.credits ?? user?.credit_balance ?? 0
    const fee = quota?.creation_fee ?? 500
    if (currentBalance < fee && user?.role !== 'admin') {
      toast.error(`Số dư của bạn không đủ (${currentBalance}/${fee} Credits). Vui lòng nạp thêm credit.`)
      return
    }

    setIsSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('name', name.trim())
      if (description.trim()) {
        formData.append('description', description.trim())
      }
      formData.append('gender', gender)
      formData.append('language', 'vi-VN')
      formData.append('consent_accepted', 'true')
      formData.append('audio_file', fileToUpload)

      const newVoice = await createVoiceClone(formData)
      toast.success(`Đã tạo thành công giọng clone '${newVoice.name}'!`)

      await refreshUser()
      if (onVoiceCreated) {
        onVoiceCreated(newVoice)
      }
      onClose()
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error).message ||
        'Không thể tạo giọng clone lúc này.'
      toast.error(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  const isFormValid =
    name.trim().length > 0 &&
    consentAccepted &&
    ((mode === 'record' && audioBlob !== null && recordingSeconds >= 5) ||
      (mode === 'upload' && uploadedFile !== null))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="relative w-full max-w-xl max-h-[92vh] rounded-2xl bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-2xl flex flex-col overflow-hidden text-slate-900 dark:text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-50/60 dark:bg-[#0B0D12]/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold">Clone Giọng Nói Cá Nhân</h2>
              <p className="text-xs text-slate-500 dark:text-white/40">
                Tạo bản sao giọng nói độc quyền từ mẫu thu âm 5–30 giây
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body (scrollable) */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {/* Quota & Cost Header Card */}
          <div className="p-3 sm:p-3.5 rounded-xl border border-indigo-100 dark:border-indigo-950/60 bg-indigo-50/50 dark:bg-indigo-950/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Coins className="w-4 h-4 text-amber-500 flex-shrink-0" />
              <span>
                Phí tạo 1 lần:{' '}
                <strong className="text-indigo-600 dark:text-indigo-400">
                  {quota?.creation_fee ?? 500} Credits
                </strong>{' '}
                (đọc văn bản x{quota?.multiplier ?? 1.5})
              </span>
            </div>
            <div className="text-right text-[11px] text-slate-500 dark:text-white/50">
              Đã dùng:{' '}
              <strong className="text-slate-800 dark:text-white">
                {quota?.used ?? 0}/{quota?.max_allowed ?? 1}
              </strong>{' '}
              giọng
            </div>
          </div>

          {/* Mode Tabs: Ghi âm trực tiếp vs Tải tệp */}
          <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-slate-100 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.06] text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setMode('record')
                if (audioPlayerRef.current) audioPlayerRef.current.pause()
              }}
              className={`py-2 rounded-lg flex items-center justify-center gap-2 transition-all ${
                mode === 'record'
                  ? 'bg-white dark:bg-[#0B0D12] text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Mic className="w-4 h-4" />
              <span>Ghi âm trực tiếp (5–30s)</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('upload')
                stopRecording()
                if (audioPlayerRef.current) audioPlayerRef.current.pause()
              }}
              className={`py-2 rounded-lg flex items-center justify-center gap-2 transition-all ${
                mode === 'upload'
                  ? 'bg-white dark:bg-[#0B0D12] text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span>Tải tệp âm thanh</span>
            </button>
          </div>

          {/* Mode 1: Ghi âm trực tiếp */}
          {mode === 'record' && (
            <div className="p-4 sm:p-5 rounded-2xl border border-dashed border-slate-300 dark:border-white/[0.1] bg-slate-50/50 dark:bg-[#181C25]/40 flex flex-col items-center justify-center text-center space-y-3">
              <div className="text-2xl font-mono font-bold tracking-wider text-slate-800 dark:text-white">
                00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds} / 00:30
              </div>

              {!isRecording ? (
                <button
                  type="button"
                  onClick={startRecording}
                  className="px-5 py-2.5 rounded-full bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-rose-600/30 transition-all hover:scale-105"
                >
                  <Mic className="w-4 h-4" />
                  <span>{audioBlob ? 'Thu âm lại từ đầu' : 'Bắt đầu ghi âm'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopRecording}
                  className="px-5 py-2.5 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-semibold text-xs flex items-center gap-2 shadow-lg transition-all animate-pulse"
                >
                  <Square className="w-4 h-4 fill-current" />
                  <span>Dừng thu âm ({recordingSeconds}s)</span>
                </button>
              )}

              <p className="text-[11px] text-slate-500 dark:text-white/40 max-w-sm">
                Hãy đọc rõ ràng một đoạn văn bản ngắn trong phòng yên tĩnh. Mẫu âm thanh đạt từ 10–25 giây
                sẽ cho chất lượng giọng clone tốt nhất.
              </p>

              {/* Nghe lại mẫu thu âm */}
              {audioUrl && !isRecording && (
                <div className="w-full pt-3 mt-1 border-t border-slate-200 dark:border-white/[0.08] flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    Đã thu {recordingSeconds} giây
                  </span>
                  <button
                    type="button"
                    onClick={togglePlayAudio}
                    className="px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold flex items-center gap-1.5 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors"
                  >
                    {isPlayingAudio ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                    <span>{isPlayingAudio ? 'Tạm dừng' : 'Nghe lại'}</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Mode 2: Tải tệp âm thanh */}
          {mode === 'upload' && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="p-6 rounded-2xl border-2 border-dashed border-slate-300 dark:border-white/[0.12] hover:border-indigo-500 dark:hover:border-indigo-400 bg-slate-50/50 dark:bg-[#181C25]/40 flex flex-col items-center justify-center text-center cursor-pointer transition-colors group"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp3,.wav,.m4a,.ogg,.flac"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                <Upload className="w-6 h-6" />
              </div>
              <p className="text-xs font-semibold text-slate-800 dark:text-white">
                {uploadedFile ? uploadedFile.name : 'Nhấp để chọn tệp hoặc kéo thả vào đây'}
              </p>
              <p className="text-[11px] text-slate-500 dark:text-white/40 mt-1">
                Hỗ trợ MP3, WAV, M4A, FLAC (5–30 giây, dung lượng tối đa 25MB)
              </p>

              {audioUrl && (
                <div
                  className="mt-3 pt-3 border-t border-slate-200 dark:border-white/[0.08] w-full flex items-center justify-between"
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="text-[11px] text-slate-600 dark:text-white/60">
                    Kích thước: {(uploadedFile?.size ? uploadedFile.size / 1024 : 0).toFixed(0)} KB
                  </span>
                  <button
                    type="button"
                    onClick={togglePlayAudio}
                    className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 text-xs font-semibold flex items-center gap-1.5"
                  >
                    {isPlayingAudio ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                    <span>{isPlayingAudio ? 'Tạm dừng' : 'Nghe thử'}</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Thông tin giọng đọc */}
          <div className="space-y-3.5">
            <div>
              <label className="text-xs font-bold text-slate-800 dark:text-white block mb-1">
                Tên giọng đọc clone <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ví dụ: Giọng Đọc của Hoàng, Giọng Kể Chuyện Podcast..."
                maxLength={80}
                required
                className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-800 dark:text-white block mb-1">
                  Giới tính giọng
                </label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value as 'male' | 'female' | 'unspecified')}
                  className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="male">Nam (Male)</option>
                  <option value="female">Nữ (Female)</option>
                  <option value="unspecified">Khác / Chưa xác định</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-800 dark:text-white block mb-1">
                  Mô tả phong cách
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Trầm ấm, truyền cảm, tin tức..."
                  maxLength={150}
                  className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Điều khoản bản quyền & Cam kết chống lạm dụng (BẮT BUỘC THEO PROMPT 10) */}
          <div className="p-3.5 rounded-xl border border-amber-200/80 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-950/20 space-y-2">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="text-xs font-bold text-amber-900 dark:text-amber-300">
                  Bảo vệ bản quyền & Chống lạm dụng (Bắt buộc)
                </span>
                <p className="text-[11px] text-amber-800/80 dark:text-amber-300/70 leading-relaxed">
                  Voxify nghiêm cấm clone giọng người nổi tiếng, chính trị gia hoặc người khác khi chưa có
                  văn bản đồng ý hợp pháp. Mọi hành vi giả mạo sẽ bị xóa vĩnh viễn và lưu vết phục vụ điều
                  tra.
                </p>
              </div>
            </div>

            <label className="flex items-start gap-2.5 pt-2 border-t border-amber-200/60 dark:border-amber-900/30 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={consentAccepted}
                onChange={(e) => setConsentAccepted(e.target.checked)}
                className="mt-0.5 w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
              />
              <span className="text-xs font-semibold text-slate-800 dark:text-white leading-snug">
                Đây là giọng của tôi hoặc tôi có sự đồng ý bằng văn bản của chủ giọng.
              </span>
            </label>
          </div>
        </form>

        {/* Footer actions */}
        <div className="p-4 sm:p-5 border-t border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-50/60 dark:bg-[#0B0D12]/60">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 dark:text-white/60 dark:hover:text-white transition-colors"
          >
            Hủy bỏ
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isFormValid || isSubmitting}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
              isFormValid && !isSubmitting
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-md shadow-indigo-600/30'
                : 'bg-slate-200 dark:bg-white/10 text-slate-400 dark:text-white/30 cursor-not-allowed'
            }`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang xử lý & phân tích giọng...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Tạo giọng Clone</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
