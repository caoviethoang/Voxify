import { useState, useCallback, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useAppConfig } from '../hooks/useAppConfig'
import { useVoices } from '../hooks/useVoices'
import { useTTS } from '../hooks/useTTS'
import { useTTSJob } from '../hooks/useTTSJob'
import { useToast } from '../hooks/useToast'
import VoicePicker from '../components/ui/VoicePicker'
import AudioPlayer from '../components/AudioPlayer'
import SliderControl from '../components/SliderControl'
import DictionaryModal from '../components/studio/DictionaryModal'
import BatchModal from '../components/studio/BatchModal'
import { listRecentJobs, type TTSJob } from '../api/tts'
import {
  Sliders,
  History,
  Play,
  Download,
  RotateCcw,
  Sparkles,
  BookOpen,
  Radio,
  Newspaper,
  Megaphone,
  Smile,
  ChevronRight,
  ChevronLeft,
  X,
  PauseCircle,
  BookA,
  Search,
  RefreshCw,
  Plus,
  AlertTriangle,
  Layers,
  Users,
  Trash2,
  CheckCircle2,
  Loader2,
  Upload,
  User as UserIcon,
  MessageSquare,
  ChevronDown,
  Wind,
  Mic,
  Clock,
  ExternalLink,
} from 'lucide-react'

// Mẫu văn bản theo chủ đề cho menu "Kịch bản"
const SAMPLE_PROMPTS = [
  {
    id: 'story',
    label: 'Đọc truyện',
    icon: BookOpen,
    text: 'Đêm nay, trăng sáng vằng vặc trên đỉnh núi Ba Vì. Tiếng suối róc rách len lỏi qua từng khe đá, hòa cùng tiếng gió xào xạc nơi rừng thông già...',
  },
  {
    id: 'podcast',
    label: 'Podcast',
    icon: Radio,
    text: 'Chào mừng các bạn đã quay trở lại với tập podcast tuần này. Hôm nay chúng ta sẽ cùng bàn luận về chủ đề: Làm thế nào để duy trì sự tập trung trong kỷ nguyên số...',
  },
  {
    id: 'news',
    label: 'Tin tức',
    icon: Newspaper,
    text: 'Bản tin kinh tế sáng nay: Thị trường công nghệ trong nước ghi nhận mức tăng trưởng ấn tượng với hàng loạt giải pháp trí tuệ nhân tạo được ứng dụng vào đời sống sản xuất...',
  },
  {
    id: 'ads',
    label: 'Quảng cáo',
    icon: Megaphone,
    text: 'Bạn đang tìm kiếm giải pháp chuyển đổi giọng nói đỉnh cao? Voxify mang đến công nghệ AI vượt trội, biểu cảm tự nhiên, tối ưu hóa thời gian sản xuất nội dung của bạn!',
  },
  {
    id: 'comedy',
    label: 'Giải trí',
    icon: Smile,
    text: 'Sáu rưỡi chiều sau giờ tan làm, bạn đứng trước giá tạ với cái bụng đang réo nhẹ vì cả tuần nay đã cắt bớt nửa bát cơm để giảm mỡ bụng...',
  },
]

export default function TextToSpeech() {
  const { user, updateCredits, refreshUser } = useAuth()
  const { config } = useAppConfig()
  const { data: voiceData } = useVoices()
  const {
    isLoading: isPreviewLoading,
    currentUrl: previewUrl,
    generate: generatePreview,
  } = useTTS()
  const {
    activeJob,
    isJobRunning,
    jobProgress,
    jobError,
    startJob,
    getJobAudioUrl,
    getJobSubtitleUrl,
  } = useTTSJob()
  const toast = useToast()

  // State văn bản & thông số
  const [text, setText] = useState('')
  const [selectedVoiceId, setSelectedVoiceId] = useState('')
  const [rate, setRate] = useState(0)
  const [pitch, setPitch] = useState(0)
  const [volume, setVolume] = useState(0)
  const [outputFormat, setOutputFormat] = useState<'mp3' | 'wav'>('mp3')
  const [applyDictionary, setApplyDictionary] = useState(true)
  const [voiceStyle, setVoiceStyle] = useState<'story' | 'natural' | 'expressive'>('natural')

  // Chế độ soạn thảo (Đơn giọng, Nhiều giọng, Phụ đề)
  const [editorMode, setEditorMode] = useState<'single' | 'multi' | 'subtitle'>('single')

  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Modals & Menus state
  const [isVoicePickerOpen, setIsVoicePickerOpen] = useState(false)
  const [isDictionaryModalOpen, setIsDictionaryModalOpen] = useState(false)
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false)
  const [isMultiVoiceMenuOpen, setIsMultiVoiceMenuOpen] = useState(false)
  const [isScriptMenuOpen, setIsScriptMenuOpen] = useState(false)

  // Right panel: Tab & Collapse
  const [rightPanelTab, setRightPanelTab] = useState<'settings' | 'history'>('settings')
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)

  // Recent jobs from server
  const [recentJobs, setRecentJobs] = useState<TTSJob[]>([])
  const [isFetchingRecentJobs, setIsFetchingRecentJobs] = useState(false)
  const [historySearch, setHistorySearch] = useState('')

  // Replay state
  const [replayUrl, setReplayUrl] = useState<string | null>(null)
  const [replayVoice, setReplayVoice] = useState('')
  const [replayIsPreview, setReplayIsPreview] = useState(false)
  const [replayFormat, setReplayFormat] = useState<'mp3' | 'wav'>('mp3')
  const [replayDuration, setReplayDuration] = useState(0)
  const [replaySrtUrl, setReplaySrtUrl] = useState<string | undefined>()
  const [replayVttUrl, setReplayVttUrl] = useState<string | undefined>()

  const voices = voiceData?.voices ?? []

  // Khởi tạo giọng mặc định
  useEffect(() => {
    if (!selectedVoiceId && config?.default_voice) {
      setSelectedVoiceId(config.default_voice)
    } else if (!selectedVoiceId && voices.length > 0) {
      setSelectedVoiceId(voices[0].id)
    }
  }, [config?.default_voice, voices, selectedVoiceId])

  const selectedVoice = voices.find((v) => v.id === selectedVoiceId)
  const selectedVoiceName = selectedVoice?.name ?? selectedVoiceId

  const location = useLocation()
  const appliedJobIdRef = useRef<number | null>(null)

  // Khôi phục văn bản và cài đặt khi người dùng bấm "Mở lại" từ trang Lịch sử
  useEffect(() => {
    const job = (location.state as { reopenJob?: TTSJob })?.reopenJob
    if (job && appliedJobIdRef.current !== job.id) {
      appliedJobIdRef.current = job.id
      if (job.text) setText(job.text)
      if (job.voice) setSelectedVoiceId(job.voice)
      if (job.rate) {
        const parsedRate = parseInt(job.rate.replace('%', ''))
        if (!isNaN(parsedRate)) setRate(parsedRate)
      }
      if (job.pitch) {
        const parsedPitch = parseInt(job.pitch.replace('Hz', ''))
        if (!isNaN(parsedPitch)) setPitch(parsedPitch)
      }
      if (job.volume) {
        const parsedVolume = parseInt(job.volume.replace('%', ''))
        if (!isNaN(parsedVolume)) setVolume(parsedVolume)
      }
      if (job.format === 'mp3' || job.format === 'wav') {
        setOutputFormat(job.format)
      }
      if (job.audio_url) {
        setReplayUrl(job.audio_url)
        setReplayVoice(voices.find((v) => v.id === job.voice)?.name || job.voice)
        setReplayIsPreview(false)
        setReplayFormat((job.format as 'mp3' | 'wav') || 'mp3')
        setReplayDuration(job.duration || 0)
        if (job.srt_url) setReplaySrtUrl(job.srt_url)
        if (job.vtt_url) setReplayVttUrl(job.vtt_url)
      }
      toast.info('Đã nạp lại văn bản và cài đặt từ lịch sử.')
    }
  }, [location.state, voices, toast])

  const rateStr = `${rate >= 0 ? '+' : ''}${rate}%`
  const pitchStr = `${pitch >= 0 ? '+' : ''}${pitch}Hz`
  const volumeStr = `${volume >= 0 ? '+' : ''}${volume}%`

  const userId = user?.id

  // Tải danh sách recent jobs từ backend
  const fetchRecentJobs = useCallback(async () => {
    if (!userId) return
    setIsFetchingRecentJobs(true)
    try {
      const data = await listRecentJobs(30)
      setRecentJobs(data)
    } catch (err) {
      console.warn('Lỗi tải danh sách job gần đây:', err)
    } finally {
      setIsFetchingRecentJobs(false)
    }
  }, [userId])

  useEffect(() => {
    if (userId) {
      fetchRecentJobs()
    }
  }, [userId, fetchRecentJobs])

  // Theo dõi trạng thái hoàn thành của job hiện tại
  const wasRunningRef = useRef(false)

  useEffect(() => {
    if (isJobRunning) {
      wasRunningRef.current = true
    } else if (wasRunningRef.current) {
      wasRunningRef.current = false
      if (activeJob?.status === 'done') {
        fetchRecentJobs()
        refreshUser()
        toast.success('Đã tạo xong tệp âm thanh chất lượng cao!')
      }
    }
  }, [isJobRunning, activeJob?.status, fetchRecentJobs, refreshUser, toast])

  // Ước tính số credit tiêu tốn (1 credit = 1 ký tự)
  const estimatedCredits = text.length
  const userBalance = user?.credits ?? 0
  const isInsufficient = text.trim().length > 0 && estimatedCredits > userBalance

  // Xử lý tạo giọng nói (Bất đồng bộ qua Worker nền)
  const handleGenerateJob = async () => {
    if (!text.trim()) {
      toast.error('Vui lòng nhập văn bản trước khi tạo giọng nói.')
      return
    }

    if (!user) {
      toast.error('Vui lòng đăng nhập để sử dụng tính năng tạo giọng nói.')
      return
    }

    if (estimatedCredits > userBalance) {
      toast.error(
        `Số dư credit không đủ (${userBalance.toLocaleString('vi-VN')} / ${estimatedCredits.toLocaleString(
          'vi-VN'
        )} credit). Vui lòng nạp thêm credit.`
      )
      return
    }

    const voice = selectedVoiceId || config.default_voice || 'vi-VN-HoaiMyNeural'
    setReplayUrl(null)

    try {
      await startJob({
        text: text.trim(),
        voice,
        rate: rateStr,
        pitch: pitchStr,
        volume: volumeStr,
        format: outputFormat,
        apply_dictionary: applyDictionary,
      })
      toast.info('Tác vụ tạo giọng nói đã được đưa vào hàng đợi xử lý.')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Lỗi khi tạo tác vụ'
      toast.error(msg)
    }
  }

  // Xử lý nghe thử 200 ký tự (Miễn phí qua API tts nhanh)
  const handlePreview = async () => {
    if (!text.trim()) {
      toast.error('Vui lòng nhập văn bản trước khi nghe thử.')
      return
    }

    const voice = selectedVoiceId || config.default_voice || 'vi-VN-HoaiMyNeural'
    setReplayUrl(null)

    try {
      const result = await generatePreview({
        text: text.trim().substring(0, 200),
        voice,
        voiceName: selectedVoiceName,
        rate: rateStr,
        pitch: pitchStr,
        volume: volumeStr,
        preview: true,
      })

      if (!result) return

      if (typeof result.creditBalance === 'number') {
        updateCredits(result.creditBalance)
      } else {
        refreshUser()
      }

      toast.success('Đã tạo bản nghe thử 200 ký tự miễn phí!')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Lỗi khi nghe thử'
      toast.error(msg)
    }
  }

  // Phím tắt Ctrl+Enter hoặc Cmd+Enter để tạo nhanh
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        if (!isJobRunning && !isPreviewLoading && text.trim() && !isInsufficient) {
          handleGenerateJob()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleGenerateJob, isJobRunning, isPreviewLoading, text, isInsufficient])

  // Chèn khoảng nghỉ vào textarea
  const insertPause = (milliseconds: number) => {
    if (!textareaRef.current) return
    const el = textareaRef.current
    const start = el.selectionStart
    const end = el.selectionEnd
    const pauseTag = ` [pause ${milliseconds >= 1000 ? `${milliseconds / 1000}s` : `${milliseconds}ms`}] `
    const newText = text.substring(0, start) + pauseTag + text.substring(end)
    setText(newText)
    setTimeout(() => {
      el.focus()
      el.setSelectionRange(start + pauseTag.length, start + pauseTag.length)
    }, 0)
    toast.info(`Đã chèn ngắt nghỉ ${milliseconds >= 1000 ? `${milliseconds / 1000}s` : `${milliseconds}ms`}`)
  }

  // Chèn thẻ cảm xúc / âm thanh tự nhiên
  const insertEmotionTag = (tag: string, label: string) => {
    if (!textareaRef.current) return
    const el = textareaRef.current
    const start = el.selectionStart
    const end = el.selectionEnd
    const formattedTag = ` [${tag}] `
    const newText = text.substring(0, start) + formattedTag + text.substring(end)
    setText(newText)
    setTimeout(() => {
      el.focus()
      el.setSelectionRange(start + formattedTag.length, start + formattedTag.length)
    }, 0)
    toast.info(`Đã chèn hiệu ứng: ${label}`)
  }

  // Chèn thẻ đa giọng [Voice: VoiceName]
  const insertVoiceTag = (voiceId: string) => {
    if (!textareaRef.current) return
    const v = voices.find((item) => item.id === voiceId)
    const voiceAlias = v?.name.split(' - ')[0] || voiceId
    const el = textareaRef.current
    const start = el.selectionStart
    const end = el.selectionEnd
    const voiceTag = `\n[Voice: ${voiceAlias}] `
    const newText = text.substring(0, start) + voiceTag + text.substring(end)
    setText(newText)
    setIsMultiVoiceMenuOpen(false)
    setTimeout(() => {
      el.focus()
      el.setSelectionRange(start + voiceTag.length, start + voiceTag.length)
    }, 0)
    toast.info(`Đã chèn đoạn kịch bản giọng ${voiceAlias}`)
  }

  // Đặt lại các thanh trượt
  const handleResetSliders = () => {
    setRate(0)
    setPitch(0)
    setVolume(0)
    setVoiceStyle('natural')
    toast.info('Đã đặt lại các thông số âm thanh về mặc định.')
  }

  // Xóa nội dung văn bản
  const handleClearText = () => {
    if (!text.trim()) return
    setText('')
    toast.info('Đã xóa nội dung văn bản.')
  }

  // Xử lý tải file văn bản lên (.txt, .docx, .srt, .vtt)
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result as string
      if (content) {
        setText(content)
        toast.success(`Đã nạp nội dung từ tệp "${file.name}"`)
      }
    }
    reader.onerror = () => {
      toast.error('Không thể đọc tệp văn bản này.')
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  // Nạp lại cấu hình từ một job đã hoàn thành
  const handleReplayJob = (job: TTSJob) => {
    setReplayUrl(getJobAudioUrl(job.id))
    setReplayVoice(voices.find((v) => v.id === job.voice)?.name || job.voice)
    setReplayIsPreview(false)
    setReplayFormat((job.format as 'mp3' | 'wav') || 'mp3')
    setReplayDuration(job.duration || 0)
    setReplaySrtUrl(getJobSubtitleUrl(job.id, 'srt'))
    setReplayVttUrl(getJobSubtitleUrl(job.id, 'vtt'))
  }

  // Nạp text và giọng vào editor
  const handleLoadJobIntoEditor = (job: TTSJob) => {
    setText(job.text)
    if (job.voice) setSelectedVoiceId(job.voice)
    if (job.rate) {
      const r = parseInt(job.rate.replace('%', ''))
      if (!isNaN(r)) setRate(r)
    }
    if (job.pitch) {
      const p = parseInt(job.pitch.replace('Hz', ''))
      if (!isNaN(p)) setPitch(p)
    }
    if (job.volume) {
      const v = parseInt(job.volume.replace('%', ''))
      if (!isNaN(v)) setVolume(v)
    }
    toast.success('Đã nạp văn bản và cài đặt vào ô soạn thảo.')
  }

  // Xác định audio URL đang hiển thị trên Player
  const hasActiveJobDone = activeJob && activeJob.status === 'done'
  const activeUrl = replayUrl || (hasActiveJobDone ? getJobAudioUrl(activeJob.id) : previewUrl)
  const activeVoiceName = replayUrl
    ? replayVoice
    : hasActiveJobDone
    ? voices.find((v) => v.id === activeJob.voice)?.name || activeJob.voice
    : selectedVoiceName
  const activeDuration = replayUrl ? replayDuration : hasActiveJobDone ? activeJob.duration : 0
  const activeFormat = replayUrl ? replayFormat : hasActiveJobDone ? (activeJob.format as 'mp3' | 'wav') : outputFormat
  const activeSrtUrl = replayUrl ? replaySrtUrl : hasActiveJobDone ? getJobSubtitleUrl(activeJob.id, 'srt') : undefined
  const activeVttUrl = replayUrl ? replayVttUrl : hasActiveJobDone ? getJobSubtitleUrl(activeJob.id, 'vtt') : undefined
  const activeIsPreview = replayUrl ? replayIsPreview : !hasActiveJobDone && Boolean(previewUrl)

  // Danh sách job được lọc trong tab lịch sử
  const filteredJobs = recentJobs.filter((item) =>
    historySearch ? item.text.toLowerCase().includes(historySearch.toLowerCase()) : true
  )

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-5 h-[calc(100vh-125px)] min-h-[620px] animate-in fade-in duration-200">
      {/* =========================================================================
          CỘT CHÍNH (GIỮA): Ô NHẬP VĂN BẢN FULL MÀN HÌNH (THEO LAYOUT ẢNH 1 YUPVOX)
      ========================================================================= */}
      <div className="flex-1 min-w-0 flex flex-col h-full rounded-2xl bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-sm overflow-hidden">
        {/* 1. Header toolbar trên cùng của ô soạn thảo */}
        <div className="flex-shrink-0 px-4 py-3 border-b border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/60 flex flex-wrap items-center justify-between gap-2.5">
          {/* Nhóm Tabs chế độ: Đơn giọng | Nhiều giọng | Phụ đề */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setEditorMode('single')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-semibold transition-all ${
                editorMode === 'single'
                  ? 'bg-white dark:bg-[#181C25] text-indigo-600 dark:text-indigo-400 border border-slate-200 dark:border-white/[0.1] shadow-xs'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <UserIcon className="w-3.5 h-3.5" />
              <span>Đơn giọng</span>
            </button>

            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setEditorMode('multi')
                  setIsMultiVoiceMenuOpen(!isMultiVoiceMenuOpen)
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-semibold transition-all ${
                  editorMode === 'multi'
                    ? 'bg-white dark:bg-[#181C25] text-purple-600 dark:text-purple-400 border border-slate-200 dark:border-white/[0.1] shadow-xs'
                    : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
                }`}
              >
                <Users className="w-3.5 h-3.5 text-purple-500" />
                <span>Nhiều giọng</span>
                <ChevronDown className="w-3 h-3 opacity-60" />
              </button>

              {/* Menu chèn thẻ giọng */}
              {isMultiVoiceMenuOpen && (
                <div className="absolute left-0 top-full mt-1.5 w-60 bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] rounded-control shadow-xl p-1.5 z-40 animate-in fade-in zoom-in-95 duration-100">
                  <div className="p-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
                    <span>Chọn giọng chèn vào kịch bản</span>
                    <button
                      onClick={() => setIsMultiVoiceMenuOpen(false)}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="max-h-52 overflow-y-auto py-1 space-y-0.5 scrollbar-thin">
                    {voices.map((v) => (
                      <button
                        key={v.id}
                        onClick={() => insertVoiceTag(v.id)}
                        className="w-full text-left px-2.5 py-1.5 rounded text-xs text-slate-800 dark:text-white/90 hover:bg-indigo-50 dark:hover:bg-white/5 transition-colors flex items-center justify-between"
                      >
                        <span className="truncate font-medium">{v.name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {v.gender === 'Female' ? 'Nữ' : 'Nam'}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                setEditorMode('subtitle')
                toast.info('Chế độ phụ đề tự động tạo file .srt và .vtt kèm theo mốc thời gian chuẩn xác.')
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-semibold transition-all ${
                editorMode === 'subtitle'
                  ? 'bg-white dark:bg-[#181C25] text-amber-600 dark:text-amber-400 border border-slate-200 dark:border-white/[0.1] shadow-xs'
                  : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 text-amber-500" />
              <span>Phụ đề</span>
            </button>
          </div>

          {/* Nhóm công cụ bên phải: Kịch bản mẫu, Từ điển, Hàng loạt, Xóa */}
          <div className="flex items-center gap-2">
            {/* Menu Kịch bản mẫu */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsScriptMenuOpen(!isScriptMenuOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] hover:border-indigo-500/50 text-xs font-medium text-slate-700 dark:text-white/90 transition-all shadow-xs"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                <span>Kịch bản</span>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {isScriptMenuOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-64 bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] rounded-control shadow-xl p-1.5 z-40 animate-in fade-in zoom-in-95 duration-100">
                  <div className="p-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-white/[0.06]">
                    Chọn văn bản mẫu
                  </div>
                  <div className="py-1 space-y-0.5">
                    {SAMPLE_PROMPTS.map((sample) => {
                      const Icon = sample.icon
                      return (
                        <button
                          key={sample.id}
                          onClick={() => {
                            setText(sample.text)
                            setIsScriptMenuOpen(false)
                            toast.info(`Đã nạp kịch bản mẫu: ${sample.label}`)
                          }}
                          className="w-full text-left px-2.5 py-2 rounded text-xs text-slate-800 dark:text-white/90 hover:bg-indigo-50 dark:hover:bg-white/5 transition-colors flex items-center gap-2.5 group"
                        >
                          <Icon className="w-3.5 h-3.5 text-indigo-500 group-hover:scale-110 transition-transform" />
                          <div>
                            <p className="font-semibold">{sample.label}</p>
                            <p className="text-[10px] text-slate-400 truncate max-w-[190px]">{sample.text}</p>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Từ điển phát âm */}
            <button
              type="button"
              onClick={() => setIsDictionaryModalOpen(true)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 text-xs text-slate-700 dark:text-white/70 hover:text-slate-900 dark:hover:text-white transition-colors"
              title="Từ điển phát âm cá nhân"
            >
              <BookA className="w-3.5 h-3.5 text-indigo-500" />
              <span>Từ điển</span>
            </button>

            {/* Tạo hàng loạt */}
            <button
              type="button"
              onClick={() => setIsBatchModalOpen(true)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 text-xs text-slate-700 dark:text-white/70 hover:text-slate-900 dark:hover:text-white transition-colors"
              title="Tạo giọng nói hàng loạt từ file văn bản"
            >
              <Layers className="w-3.5 h-3.5 text-emerald-500" />
              <span>Hàng loạt</span>
            </button>

            {/* Xóa nội dung */}
            {text.trim() && (
              <button
                type="button"
                onClick={handleClearText}
                className="p-1.5 rounded-control text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                title="Xóa toàn bộ văn bản"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Nút bật/tắt settings trên mobile (< 1024px) */}
            <button
              type="button"
              onClick={() => setMobileDrawerOpen(true)}
              className="lg:hidden flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-100 hover:bg-slate-200 dark:bg-[#181C25] dark:hover:bg-[#202532] text-xs font-semibold text-slate-800 dark:text-white"
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-500" />
              <span>Cài đặt</span>
            </button>
          </div>
        </div>

        {/* 2. Ô soạn thảo mở rộng toàn màn hình (Full viewport editor body) */}
        <div className="flex-1 min-h-0 relative flex flex-col p-4 sm:p-6 overflow-hidden">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Nhập hoặc dán nội dung văn bản cần chuyển đổi thành giọng nói..."
            className="flex-1 w-full bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 text-sm sm:text-base leading-relaxed focus:outline-none resize-none font-sans overflow-y-auto scrollbar-thin"
          />

          {/* Dòng gợi ý nhanh khi ô soạn thảo trống */}
          {!text.trim() && (
            <div className="flex-shrink-0 pt-3 border-t border-slate-100 dark:border-white/[0.04] mt-2">
              <span className="text-[11px] text-slate-400 dark:text-white/40 block mb-2 font-medium">
                Gợi ý mẫu thử giọng nhanh:
              </span>
              <div className="flex flex-wrap items-center gap-2">
                {SAMPLE_PROMPTS.slice(0, 3).map((sample) => (
                  <button
                    key={sample.id}
                    onClick={() => setText(sample.text)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#1e232f] border border-slate-200 dark:border-white/[0.06] text-xs text-slate-700 dark:text-white/80 hover:border-indigo-500/40 transition-all"
                  >
                    <span>{sample.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Thanh tiến độ khi Worker đang xử lý job */}
        {isJobRunning && (
          <div className="flex-shrink-0 px-5 py-3 bg-indigo-50/90 dark:bg-indigo-950/40 border-t border-indigo-100 dark:border-indigo-500/20 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-semibold">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600 dark:text-indigo-400" />
                <span>Đang tổng hợp giọng nói qua worker nền...</span>
              </div>
              <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                {jobProgress}%
              </span>
            </div>
            <div className="w-full bg-indigo-200/60 dark:bg-indigo-900/40 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-indigo-600 dark:bg-indigo-400 h-full transition-all duration-300 rounded-full"
                style={{ width: `${jobProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Báo lỗi nếu job thất bại */}
        {jobError && (
          <div className="flex-shrink-0 px-5 py-2.5 bg-rose-50 dark:bg-rose-950/30 border-t border-rose-200 dark:border-rose-500/20 flex items-center justify-between text-xs text-rose-700 dark:text-rose-300">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>{jobError}</span>
            </div>
          </div>
        )}

        {/* Audio Player tích hợp ngay dưới ô soạn thảo khi có audio */}
        {activeUrl && (
          <div className="flex-shrink-0 px-4 py-2 border-t border-slate-100 dark:border-white/[0.06] bg-slate-50/50 dark:bg-[#0B0D12]/40">
            <AudioPlayer
              url={activeUrl}
              voiceName={activeVoiceName}
              isPreview={activeIsPreview}
              duration={activeDuration}
              format={activeFormat}
              srtUrl={activeSrtUrl}
              vttUrl={activeVttUrl}
            />
          </div>
        )}

        {/* 3. Footer Toolbar dưới cùng: Tải file, Chèn ngắt nghỉ, Bộ đếm ký tự & Nút Tạo giọng nói */}
        <div className="flex-shrink-0 p-3 sm:px-5 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/70 flex flex-wrap items-center justify-between gap-3">
          {/* Nhóm thao tác file & chèn cú pháp bên trái */}
          <div className="flex items-center gap-2">
            {/* Input file ẩn */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.docx,.srt,.vtt,.md"
              onChange={handleFileUpload}
              className="hidden"
            />
            {/* Nút Upload file */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-control bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] hover:border-indigo-500/50 text-slate-700 hover:text-indigo-600 dark:text-white/80 dark:hover:text-white transition-all shadow-xs"
              title="Tải lên tệp văn bản (.txt, .docx, .srt, .vtt)"
            >
              <Upload className="w-4 h-4" />
            </button>

            {/* Nút chèn ngắt nghỉ */}
            <button
              type="button"
              onClick={() => insertPause(1000)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] hover:border-indigo-500/50 text-xs font-medium text-slate-700 hover:text-indigo-600 dark:text-white/80 dark:hover:text-white transition-all shadow-xs"
              title="Chèn dấu ngắt nghỉ [pause 1s]"
            >
              <PauseCircle className="w-3.5 h-3.5 text-indigo-500" />
              <span>Ngắt nghỉ (1s)</span>
            </button>
          </div>

          {/* Nhóm thông tin credit & Nút Tạo giọng nói bên phải */}
          <div className="flex items-center gap-3">
            {/* Bộ đếm ký tự & ước tính credit */}
            <div className="text-right text-xs">
              <span className="font-mono text-slate-600 dark:text-white/70">
                {text.length.toLocaleString('vi-VN')}
                <span className="text-slate-400 dark:text-white/40"> / 28.000 ký tự</span>
              </span>
              {text.trim().length > 0 && (
                <div className="text-[11px] font-medium">
                  {isInsufficient ? (
                    <span className="text-rose-600 dark:text-rose-400">
                      Thiếu credit ({userBalance.toLocaleString('vi-VN')} / {estimatedCredits.toLocaleString('vi-VN')})
                    </span>
                  ) : (
                    <span className="text-slate-400 dark:text-white/40">
                      ~{estimatedCredits.toLocaleString('vi-VN')} credit
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Nút Nạp thêm nếu thiếu credit */}
            {isInsufficient && (
              <Link
                to="/pricing"
                className="flex items-center gap-1 px-3 py-2 rounded-control bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold shadow-xs transition-all"
                title="Bấm để nạp thêm credit"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Nạp thêm</span>
              </Link>
            )}

            {/* Nút Nghe thử 200 ký tự */}
            <button
              type="button"
              onClick={handlePreview}
              disabled={isPreviewLoading || isJobRunning || !text.trim()}
              className="hidden sm:flex items-center gap-1.5 px-3.5 py-2 rounded-control bg-white hover:bg-slate-50 dark:bg-transparent dark:hover:bg-white/5 border border-slate-200 dark:border-white/[0.1] hover:border-slate-300 dark:hover:border-white/[0.2] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-slate-700 dark:text-white transition-all shadow-xs"
            >
              {isPreviewLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              <span>Nghe thử (200 ký tự)</span>
            </button>

            {/* Nút Tạo giọng nói chính */}
            <button
              type="button"
              onClick={handleGenerateJob}
              disabled={isJobRunning || isPreviewLoading || !text.trim() || isInsufficient}
              className="flex items-center gap-2 px-5 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-md shadow-indigo-600/25 transition-all"
              title={
                isInsufficient
                  ? 'Số dư credit không đủ. Vui lòng nạp thêm!'
                  : 'Phím tắt: ⌘+Enter / Ctrl+Enter'
              }
            >
              {isJobRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang xử lý {jobProgress}%</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Tạo giọng nói</span>
                  <span className="hidden sm:inline-block font-mono text-[10px] text-white/70 bg-white/10 px-1 py-0.2 rounded">
                    ⌘↵
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* =========================================================================
          CỘT PHẢI: TAB "CẤU HÌNH" & TAB "LỊCH SỬ" (THEO GỢI Ý ẢNH 1 YUPVOX)
      ========================================================================= */}
      <div
        className={`hidden lg:flex flex-col h-full transition-all duration-150 rounded-2xl bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-sm overflow-hidden flex-shrink-0 ${
          rightPanelOpen ? 'w-[340px] xl:w-[370px]' : 'w-12'
        }`}
      >
        {/* Header panel bên phải với Tabs Cấu hình | Lịch sử */}
        <div className="flex-shrink-0 p-3 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-50/70 dark:bg-[#0B0D12]/60">
          {rightPanelOpen ? (
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-[#181C25] p-1 rounded-control border border-slate-200 dark:border-white/[0.08] text-xs font-semibold w-full mr-2">
              <button
                type="button"
                onClick={() => setRightPanelTab('settings')}
                className={`flex-1 py-1.5 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'settings'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Cấu hình</span>
              </button>

              <button
                type="button"
                onClick={() => setRightPanelTab('history')}
                className={`flex-1 py-1.5 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'history'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                <span>Lịch sử ({recentJobs.length})</span>
              </button>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <Sliders className="w-4 h-4 text-indigo-500" />
            </div>
          )}

          <button
            type="button"
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="p-1.5 rounded text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            title={rightPanelOpen ? 'Thu gọn sidebar' : 'Mở rộng sidebar'}
          >
            {rightPanelOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Nội dung Tab khi sidebar mở rộng */}
        {rightPanelOpen && (
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-5 scrollbar-thin">
            {rightPanelTab === 'settings' ? (
              /* TAB 1: CẤU HÌNH GIỌNG ĐỌC & ÂM THANH */
              <div className="space-y-5 animate-in fade-in duration-100">
                {/* 1. Chọn giọng đọc */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider block">
                    Chọn giọng đọc
                  </label>
                  <div
                    onClick={() => setIsVoicePickerOpen(true)}
                    className="p-3 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#202532] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 cursor-pointer transition-all group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-bold text-xs shadow-xs flex-shrink-0">
                        {selectedVoice?.gender === 'Female' ? '♀' : '♂'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                          {selectedVoiceName}
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-white/40 truncate">
                          {selectedVoice?.locale_name || 'Vietnamese'} &middot;{' '}
                          {selectedVoice?.gender === 'Female' ? 'Nữ' : 'Nam'}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                  </div>
                </div>

                {/* 2. Phong cách giọng đọc (Theo giao diện Yupvox) */}
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-white/[0.06]">
                  <label className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider block">
                    Phong cách giọng đọc
                  </label>
                  <div className="grid grid-cols-3 gap-1.5">
                    <button
                      type="button"
                      onClick={() => setVoiceStyle('story')}
                      className={`px-2 py-2 rounded-control text-xs font-medium transition-all text-center border ${
                        voiceStyle === 'story'
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#181C25] text-slate-700 dark:text-white/70 hover:bg-slate-100'
                      }`}
                    >
                      Kể chuyện
                    </button>
                    <button
                      type="button"
                      onClick={() => setVoiceStyle('natural')}
                      className={`px-2 py-2 rounded-control text-xs font-medium transition-all text-center border ${
                        voiceStyle === 'natural'
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#181C25] text-slate-700 dark:text-white/70 hover:bg-slate-100'
                      }`}
                    >
                      Tự nhiên
                    </button>
                    <button
                      type="button"
                      onClick={() => setVoiceStyle('expressive')}
                      className={`px-2 py-2 rounded-control text-xs font-medium transition-all text-center border ${
                        voiceStyle === 'expressive'
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#181C25] text-slate-700 dark:text-white/70 hover:bg-slate-100'
                      }`}
                    >
                      Biểu cảm
                    </button>
                  </div>
                </div>

                {/* 3. Tinh chỉnh Tốc độ đọc */}
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-white/[0.06]">
                  <SliderControl
                    label="Tốc độ đọc"
                    value={rate}
                    min={-50}
                    max={100}
                    step={5}
                    displayValue={`${(1 + rate / 100).toFixed(2)}x`}
                    scaleLabels={['Chậm hơn', 'Chuẩn', 'Nhanh hơn']}
                    onChange={setRate}
                  />
                </div>

                {/* 4. Các nút chèn cảm xúc & ngắt nghỉ nhanh (Theo giao diện Yupvox) */}
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => insertEmotionTag('cười', 'Cười')}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] hover:border-amber-400 text-xs text-slate-700 dark:text-white/80 transition-colors"
                    >
                      <Smile className="w-3.5 h-3.5 text-amber-500" />
                      <span>Cười</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => insertEmotionTag('thở dài', 'Thở dài')}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] hover:border-sky-400 text-xs text-slate-700 dark:text-white/80 transition-colors"
                    >
                      <Wind className="w-3.5 h-3.5 text-sky-500" />
                      <span>Thở dài</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => insertEmotionTag('hắng giọng', 'Hắng giọng')}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] hover:border-emerald-400 text-xs text-slate-700 dark:text-white/80 transition-colors"
                    >
                      <Mic className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Hắng giọng</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => insertPause(1000)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-400 text-xs text-slate-700 dark:text-white/80 transition-colors"
                    >
                      <Clock className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Tạm dừng...</span>
                    </button>
                  </div>
                </div>

                {/* 5. Cao độ & Âm lượng */}
                <div className="space-y-4 pt-2 border-t border-slate-100 dark:border-white/[0.06]">
                  <SliderControl
                    label="Cao độ (Pitch)"
                    value={pitch}
                    min={-50}
                    max={50}
                    step={1}
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

                {/* 6. Định dạng đầu ra */}
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-white/[0.06]">
                  <label className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider block">
                    Định dạng đầu ra
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setOutputFormat('mp3')}
                      className={`p-2.5 rounded-control border text-left transition-all ${
                        outputFormat === 'mp3'
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#181C25] text-slate-700 dark:text-white/70'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs">Audio MP3</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 font-bold">
                          Chuẩn
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-white/40 mt-1">24kHz &middot; 48kbps</p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setOutputFormat('wav')}
                      className={`p-2.5 rounded-control border text-left transition-all ${
                        outputFormat === 'wav'
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#181C25] text-slate-700 dark:text-white/70'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs">Audio WAV</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 font-bold">
                          Lossless
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-white/40 mt-1">24kHz &middot; 16-bit PCM</p>
                    </button>
                  </div>
                </div>

                {/* 7. Áp dụng từ điển phát âm */}
                <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-800 dark:text-white">Áp dụng từ điển phát âm</p>
                    <p className="text-[10px] text-slate-500 dark:text-white/40">Tự động chuẩn hóa từ viết tắt & số</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={applyDictionary}
                      onChange={(e) => setApplyDictionary(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-white/10 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                {/* 8. Nút Đặt lại mục định */}
                <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] text-right">
                  <button
                    type="button"
                    onClick={handleResetSliders}
                    className="text-xs text-slate-500 hover:text-indigo-600 dark:text-white/50 dark:hover:text-indigo-400 inline-flex items-center gap-1 font-medium transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Đặt lại mặc định</span>
                  </button>
                </div>
              </div>
            ) : (
              /* TAB 2: LỊCH SỬ XỬ LÝ (CHUYỂN TOÀN BỘ VÀO SIDEBAR PHẢI NHƯ ẢNH 1) */
              <div className="space-y-3 animate-in fade-in duration-100">
                {/* Search & Refresh */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <div className="relative flex-1">
                      <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={historySearch}
                        onChange={(e) => setHistorySearch(e.target.value)}
                        placeholder="Tìm kiếm theo nội dung, ID..."
                        className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-control pl-8 pr-2.5 py-1.5 text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                      />
                      {historySearch && (
                        <button
                          onClick={() => setHistorySearch('')}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={fetchRecentJobs}
                      disabled={isFetchingRecentJobs}
                      className="p-2 rounded-control text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-white/50 dark:hover:text-white dark:hover:bg-white/5 border border-slate-200 dark:border-white/[0.08] disabled:opacity-50 transition-colors"
                      title="Làm mới lịch sử"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isFetchingRecentJobs ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </div>

                {/* Danh sách các bản ghi */}
                {filteredJobs.length === 0 ? (
                  <div className="py-12 text-center text-slate-400 dark:text-white/30 space-y-2">
                    <History className="w-8 h-8 mx-auto opacity-30" />
                    <p className="text-xs">
                      {historySearch ? 'Không tìm thấy bản ghi phù hợp.' : 'Chưa có bản ghi nào gần đây.'}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {filteredJobs.map((item) => {
                      const itemVoice = voices.find((v) => v.id === item.voice)?.name || item.voice
                      const isDone = item.status === 'done'

                      return (
                        <div
                          key={item.id}
                          className="p-3 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#1e232f] border border-slate-200/80 dark:border-white/[0.06] transition-all space-y-2 group"
                        >
                          {/* Dòng 1: Giọng đọc + Trạng thái + Thời lượng */}
                          <div className="flex items-center justify-between text-[11px]">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <span className="font-bold text-slate-900 dark:text-white truncate max-w-[140px]">
                                {itemVoice}
                              </span>
                              <span className="text-[10px] uppercase font-mono px-1 rounded bg-slate-200/70 dark:bg-white/10 text-slate-600 dark:text-white/70">
                                {item.format || 'mp3'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              {isDone && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                                  <CheckCircle2 className="w-3 h-3" />
                                  <span>{item.duration ? `${item.duration.toFixed(1)}s` : 'OK'}</span>
                                </span>
                              )}
                              {item.status === 'processing' && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] font-mono text-indigo-600 dark:text-indigo-400">
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                  <span>{item.progress}%</span>
                                </span>
                              )}
                              {item.status === 'failed' && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-rose-500">
                                  <AlertTriangle className="w-3 h-3" />
                                  <span>Lỗi</span>
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Dòng 2: Nội dung văn bản tóm tắt */}
                          <p
                            className="text-xs text-slate-600 dark:text-white/70 line-clamp-2 leading-relaxed cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400"
                            title={item.text}
                            onClick={() => isDone && handleReplayJob(item)}
                          >
                            {item.text}
                          </p>

                          {/* Dòng 3: Thao tác Nghe, Nạp lại, Tải về */}
                          <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 dark:border-white/[0.04] text-[11px]">
                            <span className="text-[10px] font-mono text-amber-500 font-semibold">
                              {item.credit_used ?? item.char_count} credits
                            </span>

                            <div className="flex items-center gap-1">
                              {/* Nút Nghe phát */}
                              {isDone && (
                                <button
                                  type="button"
                                  onClick={() => handleReplayJob(item)}
                                  className="p-1 rounded text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-white/5 transition-colors"
                                  title="Nghe lại bản ghi này"
                                >
                                  <Play className="w-3.5 h-3.5 fill-current" />
                                </button>
                              )}

                              {/* Nút Nạp vào editor */}
                              <button
                                type="button"
                                onClick={() => handleLoadJobIntoEditor(item)}
                                className="px-1.5 py-0.5 rounded text-[10px] font-medium text-slate-600 hover:text-slate-900 dark:text-white/70 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 transition-colors"
                                title="Nạp văn bản vào ô soạn thảo"
                              >
                                Nạp lại
                              </button>

                              {/* Nút tải về nếu hoàn thành */}
                              {isDone && (
                                <a
                                  href={`/api/tts/jobs/${item.id}/audio?download=true`}
                                  download
                                  className="p-1 rounded text-slate-500 hover:text-slate-900 dark:text-white/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                                  title="Tải tệp âm thanh"
                                >
                                  <Download className="w-3.5 h-3.5" />
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Link sang trang lịch sử đầy đủ */}
                <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] text-center">
                  <Link
                    to="/history"
                    className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 inline-flex items-center gap-1 font-semibold hover:underline"
                  >
                    <span>Xem toàn bộ lịch sử chi tiết</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Drawer trượt cho màn hình nhỏ (< 1024px) */}
      {mobileDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileDrawerOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 max-w-sm w-full bg-white dark:bg-[#12151C] border-l border-slate-200 dark:border-white/[0.08] p-5 shadow-2xl z-10 overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-white/[0.08] mb-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Cài đặt giọng nói</h3>
              <button
                onClick={() => setMobileDrawerOpen(false)}
                className="p-1 rounded-control text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {/* Slider controls inside mobile drawer */}
            <div className="space-y-4">
              <SliderControl
                label="Tốc độ (Speed)"
                value={rate}
                min={-50}
                max={100}
                step={5}
                displayValue={`${(1 + rate / 100).toFixed(2)}x`}
                scaleLabels={['Chậm hơn', 'Chuẩn', 'Nhanh hơn']}
                onChange={setRate}
              />
              <SliderControl
                label="Cao độ (Pitch)"
                value={pitch}
                min={-50}
                max={50}
                step={1}
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
        </div>
      )}

      {/* VoicePicker Modal */}
      <VoicePicker
        isOpen={isVoicePickerOpen}
        onClose={() => setIsVoicePickerOpen(false)}
        voices={voices}
        selectedVoiceId={selectedVoiceId}
        onSelectVoice={(id) => {
          setSelectedVoiceId(id)
          toast.success(`Đã chọn giọng đọc ${voices.find((v) => v.id === id)?.name || id}`)
        }}
        onPreviewSample={(id) => {
          toast.info(`Đang nghe thử giọng ${voices.find((v) => v.id === id)?.name || id}`)
        }}
      />

      {/* Dictionary Modal */}
      <DictionaryModal
        isOpen={isDictionaryModalOpen}
        onClose={() => setIsDictionaryModalOpen(false)}
      />

      {/* Batch TTS Modal */}
      <BatchModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        defaultVoice={selectedVoiceId || 'vi-VN-HoaiMyNeural'}
        defaultRate={rateStr}
        defaultPitch={pitchStr}
        defaultVolume={volumeStr}
        selectedFormat={outputFormat}
        applyDictionary={applyDictionary}
      />
    </div>
  )
}
