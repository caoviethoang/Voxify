import { useState, useCallback, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useAppConfig } from '../hooks/useAppConfig'
import { useVoices } from '../hooks/useVoices'
import { useTTS } from '../hooks/useTTS'
import { useToast } from '../hooks/useToast'
import VoicePicker from '../components/ui/VoicePicker'
import AudioPlayer from '../components/AudioPlayer'
import SliderControl from '../components/SliderControl'
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
  Coins,
  ChevronRight,
  ChevronLeft,
  X,
  PauseCircle,
  BookA,
  Search,
  RefreshCw,
  Plus,
  AlertTriangle,
} from 'lucide-react'

// Mẫu văn bản theo chủ đề
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
  const { isLoading, currentUrl, history, generate, clearHistory } = useTTS()
  const toast = useToast()

  // State văn bản & thông số
  const [text, setText] = useState('')
  const [selectedVoiceId, setSelectedVoiceId] = useState('')
  const [rate, setRate] = useState(0)
  const [pitch, setPitch] = useState(0)
  const [volume, setVolume] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Right panel: Tab & Collapse
  const [rightPanelTab, setRightPanelTab] = useState<'settings' | 'history'>('settings')
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)

  // VoicePicker Modal
  const [isVoicePickerOpen, setIsVoicePickerOpen] = useState(false)

  // Replay state
  const [replayUrl, setReplayUrl] = useState<string | null>(null)
  const [replayVoice, setReplayVoice] = useState('')
  const [replayIsPreview, setReplayIsPreview] = useState(false)

  // Conversion table search & selection
  const [tableSearch, setTableSearch] = useState('')
  const [selectedTableRows, setSelectedTableRows] = useState<string[]>([])

  const voices = voiceData?.voices ?? []

  // Khởi tạo giọng mặc định
  useEffect(() => {
    if (!selectedVoiceId && config.default_voice) {
      setSelectedVoiceId(config.default_voice)
    } else if (!selectedVoiceId && voices.length > 0) {
      setSelectedVoiceId(voices[0].id)
    }
  }, [config.default_voice, voices, selectedVoiceId])

  const selectedVoice = voices.find((v) => v.id === selectedVoiceId)
  const selectedVoiceName = selectedVoice?.name ?? selectedVoiceId

  const rateStr = `${rate >= 0 ? '+' : ''}${rate}%`
  const pitchStr = `${pitch >= 0 ? '+' : ''}${pitch}Hz`
  const volumeStr = `${volume >= 0 ? '+' : ''}${volume}%`

  // Ước tính số credit tiêu tốn (1 credit = 1 ký tự)
  const estimatedCredits = text.length
  const userBalance = user?.credits ?? 0
  const isInsufficient = text.trim().length > 0 && estimatedCredits > userBalance

  // Tổng hợp giọng nói
  const handleSynthesize = useCallback(
    async (isPreview: boolean) => {
      if (!text.trim()) {
        toast.error('Vui lòng nhập văn bản trước khi tạo giọng nói.')
        return
      }

      if (!isPreview) {
        if (!user) {
          toast.error('Vui lòng đăng nhập để sử dụng tính năng tạo giọng nói đầy đủ.')
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
      }

      const voice = selectedVoiceId || config.default_voice || 'vi-VN-HoaiMyNeural'
      setReplayUrl(null)

      try {
        const result = await generate({
          text: text.trim(),
          voice,
          voiceName: selectedVoiceName,
          rate: rateStr,
          pitch: pitchStr,
          volume: volumeStr,
          preview: isPreview,
        })

        // Cập nhật số dư credit lên Topbar và Sidebar tức thì
        if (result && 'creditBalance' in result && typeof result.creditBalance === 'number') {
          updateCredits(result.creditBalance)
        } else {
          refreshUser()
        }

        toast.success(isPreview ? 'Đã tạo bản nghe thử 200 ký tự!' : 'Tổng hợp giọng nói thành công!')
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Lỗi khi tạo giọng nói'
        toast.error(msg)
      }
    },
    [
      text,
      user,
      estimatedCredits,
      userBalance,
      selectedVoiceId,
      config.default_voice,
      selectedVoiceName,
      rateStr,
      pitchStr,
      volumeStr,
      generate,
      updateCredits,
      refreshUser,
      toast,
    ]
  )

  // Phím tắt Ctrl+Enter hoặc Cmd+Enter để tạo nhanh
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        if (!isLoading && text.trim()) {
          handleSynthesize(false)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSynthesize, isLoading, text])

  // Chèn khoảng nghỉ vào textarea
  const insertPause = (milliseconds: number) => {
    if (!textareaRef.current) return
    const el = textareaRef.current
    const start = el.selectionStart
    const end = el.selectionEnd
    const pauseTag = ` [nghỉ ${milliseconds}ms] `
    const newText = text.substring(0, start) + pauseTag + text.substring(end)
    setText(newText)
    setTimeout(() => {
      el.focus()
      el.setSelectionRange(start + pauseTag.length, start + pauseTag.length)
    }, 0)
    toast.info(`Đã chèn điểm nghỉ ${milliseconds}ms`)
  }

  // Đặt lại các thanh trượt
  const handleResetSliders = () => {
    setRate(0)
    setPitch(0)
    setVolume(0)
    toast.info('Đã đặt lại các thông số âm thanh về mặc định.')
  }

  // Tải file audio
  const handleDownload = (url: string, voiceId?: string) => {
    const a = document.createElement('a')
    a.href = url
    a.download = `voxify-${voiceId || 'audio'}-${Date.now()}.mp3`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    toast.success('Bắt đầu tải file âm thanh...')
  }

  // Nạp lại cấu hình từ một bản ghi lịch sử
  const handleReplayItem = (item: (typeof history)[0]) => {
    setReplayUrl(item.url)
    setReplayVoice(item.voiceName)
    setReplayIsPreview(item.isPreview)
    setText(item.text)
    if (item.voiceId) setSelectedVoiceId(item.voiceId)
    toast.info('Đã nạp văn bản và âm thanh bản ghi.')
  }

  // Audio URL hiển thị
  const activeUrl = replayUrl || currentUrl
  const activeVoiceName = replayUrl ? replayVoice : selectedVoiceName
  const activeIsPreview = replayUrl ? replayIsPreview : false

  return (
    <div className="flex flex-col lg:flex-row gap-5 animate-in fade-in duration-200">
      {/* =========================================================================
          CỘT CHÍNH (GIỮA): SOẠN THẢO + CÔNG CỤ + ACTION BAR + BẢNG LỊCH SỬ PHIÊN
      ========================================================================= */}
      <div className="flex-1 min-w-0 space-y-5">
        {/* Hộp soạn thảo Studio chính */}
        <div className="rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col overflow-hidden">
          {/* 1. Thanh công cụ phía trên ô soạn thảo */}
          <div className="p-3 border-b border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/70 flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center gap-2">
              {/* Chip giọng đọc đang chọn */}
              <button
                onClick={() => setIsVoicePickerOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] hover:border-indigo-500/50 text-xs font-semibold text-slate-800 dark:text-white transition-all shadow-xs"
              >
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                <span className="truncate max-w-[140px]">{selectedVoiceName}</span>
                <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-mono">Đổi giọng &rarr;</span>
              </button>

              {/* Chip Tốc độ */}
              <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-control bg-slate-100 dark:bg-[#181C25] text-xs text-slate-700 dark:text-white/70 font-mono border border-slate-200/60 dark:border-transparent">
                <span className="text-[10px] text-slate-500 dark:text-white/40">Tốc độ:</span>
                <span>{rateStr}</span>
              </div>

              {/* Định dạng */}
              <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-control bg-slate-100 dark:bg-[#181C25] text-xs text-slate-700 dark:text-white/70 font-mono border border-slate-200/60 dark:border-transparent">
                <span className="text-[10px] text-slate-500 dark:text-white/40">Định dạng:</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">MP3</span>
              </div>
            </div>

            {/* Các tiện ích: Ngắt nghỉ, Từ điển, Nút mở Cài đặt mobile */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => insertPause(500)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 text-xs text-slate-700 hover:text-slate-900 dark:text-white/70 dark:hover:text-white transition-colors"
                title="Chèn dấu ngắt nghỉ tại vị trí con trỏ"
              >
                <PauseCircle className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                <span className="hidden sm:inline">Ngắt nghỉ</span>
              </button>

              <button
                onClick={() => toast.info('Tính năng Từ điển phát âm sẽ ra mắt ở phiên bản tiếp theo.')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 text-xs text-slate-700 hover:text-slate-900 dark:text-white/70 dark:hover:text-white transition-colors"
                title="Từ điển phát âm"
              >
                <BookA className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                <span className="hidden sm:inline">Từ điển</span>
              </button>

              {/* Nút mở Settings panel trên tablet/mobile */}
              <button
                onClick={() => setMobileDrawerOpen(true)}
                className="lg:hidden flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-slate-100 hover:bg-slate-200 dark:bg-[#181C25] dark:hover:bg-[#202532] text-xs text-slate-800 dark:text-white"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Cài đặt</span>
              </button>
            </div>
          </div>

          {/* 2. Ô soạn thảo rộng thoáng */}
          <div className="p-4 relative">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Nhập hoặc dán nội dung văn bản tiếng Việt bạn muốn chuyển đổi thành giọng đọc tự nhiên tại đây..."
              rows={8}
              className="w-full bg-transparent text-sm sm:text-base leading-relaxed text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none resize-none font-sans"
            />

            {/* Hàng chip ví dụ khi ô trống */}
            {!text.trim() && (
              <div className="pt-3 border-t border-slate-100 dark:border-white/[0.04]">
                <span className="text-[11px] text-slate-500 dark:text-white/40 block mb-2 font-medium">
                  Ví dụ mẫu (bấm để thử ngay):
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {SAMPLE_PROMPTS.map((sample) => {
                    const Icon = sample.icon
                    return (
                      <button
                        key={sample.id}
                        onClick={() => setText(sample.text)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#1f2430] border border-slate-200/80 dark:border-white/[0.06] hover:border-indigo-500/40 text-xs text-slate-700 hover:text-slate-900 dark:text-white/80 dark:hover:text-white transition-all group"
                      >
                        <Icon className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 group-hover:scale-110 transition-transform" />
                        <span>{sample.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* 3. Thanh hành động cố định phía dưới */}
          <div className="p-3.5 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/70 flex flex-wrap items-center justify-between gap-3">
            {/* Đếm ký tự & Credit ước tính */}
            <div className="flex items-center gap-3 text-xs">
              {/* Đếm ký tự */}
              <div className="font-mono text-slate-500 dark:text-white/50">
                <span className="text-slate-900 dark:text-white font-semibold">{text.length.toLocaleString('vi-VN')}</span>
                <span> / {config.max_chars?.toLocaleString('vi-VN') || '20.000'} ký tự</span>
              </div>

              {/* Ước tính credit tiêu tốn */}
              {estimatedCredits > 0 && (
                <div
                  className={`flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded border ${
                    isInsufficient
                      ? 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20'
                      : 'text-[#F59E0B] bg-amber-500/10 border-amber-500/20'
                  }`}
                >
                  {isInsufficient ? (
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                  ) : (
                    <Coins className="w-3.5 h-3.5 flex-shrink-0" />
                  )}
                  <span>
                    {isInsufficient
                      ? `Cần ~${estimatedCredits.toLocaleString('vi-VN')} credit (còn ${userBalance.toLocaleString('vi-VN')})`
                      : `Sẽ dùng ~${estimatedCredits.toLocaleString('vi-VN')} credit`}
                  </span>
                </div>
              )}
            </div>

            {/* Các nút hành động chính */}
            <div className="flex items-center gap-2">
              {/* Nút Nạp thêm nếu thiếu credit */}
              {isInsufficient && (
                <Link
                  to="/pricing"
                  className="flex items-center gap-1 px-3 py-2 rounded-control bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold shadow-xs transition-all"
                  title="Số dư không đủ. Bấm để nạp thêm credit"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Nạp thêm</span>
                </Link>
              )}

              {/* Nút Nghe thử */}
              <button
                type="button"
                onClick={() => handleSynthesize(true)}
                disabled={isLoading || !text.trim()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-control bg-white hover:bg-slate-50 dark:bg-transparent dark:hover:bg-white/5 border border-slate-200 dark:border-white/[0.1] hover:border-slate-300 dark:hover:border-white/[0.2] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-slate-700 dark:text-white transition-all shadow-xs"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Nghe thử (200 ký tự)</span>
              </button>

              {/* Nút Tạo giọng nói chính: Gradient Chàm -> Tím */}
              <button
                type="button"
                onClick={() => handleSynthesize(false)}
                disabled={isLoading || !text.trim() || isInsufficient}
                className="flex items-center gap-2 px-5 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all"
                title={
                  isInsufficient
                    ? 'Số dư credit không đủ. Vui lòng nạp thêm!'
                    : 'Phím tắt: ⌘+Enter / Ctrl+Enter'
                }
              >
                {isLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Đang tổng hợp...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
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

        {/* Audio Player hiển thị ngay khi tạo xong */}
        {activeUrl && (
          <AudioPlayer
            url={activeUrl}
            voiceName={activeVoiceName}
            isPreview={activeIsPreview}
            onDownload={() => handleDownload(activeUrl, selectedVoiceId)}
          />
        )}

        {/* 4. Bảng "Danh sách chuyển đổi" bên dưới */}
        <div className="rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Danh sách chuyển đổi
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-white/40">
                Toàn bộ các bản ghi giọng nói đã thực hiện trong phiên làm việc
              </p>
            </div>

            {/* Thanh công cụ bảng: Search + Refresh */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 dark:text-white/30 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  placeholder="Tìm kiếm bản ghi..."
                  className="bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-control pl-7 pr-3 py-1 text-xs text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                onClick={() => toast.info('Đã làm mới danh sách')}
                className="p-1.5 rounded-control text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-white/40 dark:hover:text-white dark:hover:bg-white/5 border border-slate-200 dark:border-white/[0.08]"
                title="Làm mới"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-white/40 border-b border-slate-200 dark:border-white/[0.06] bg-slate-50/70 dark:bg-[#0B0D12]/30">
                <tr>
                  <th className="py-2.5 px-3 w-8">
                    <input
                      type="checkbox"
                      className="rounded accent-indigo-600 cursor-pointer"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTableRows(history.map((h) => h.id))
                        } else {
                          setSelectedTableRows([])
                        }
                      }}
                    />
                  </th>
                  <th className="py-2.5 px-3">Nội dung</th>
                  <th className="py-2.5 px-3">Giọng đọc</th>
                  <th className="py-2.5 px-3">Ký tự</th>
                  <th className="py-2.5 px-3">Credit</th>
                  <th className="py-2.5 px-3">Định dạng</th>
                  <th className="py-2.5 px-3">Thời gian</th>
                  <th className="py-2.5 px-3 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400 dark:text-white/30">
                      Chưa có bản ghi âm nào được tạo. Hãy nhập văn bản và bấm "Tạo giọng nói"!
                    </td>
                  </tr>
                ) : (
                  history
                    .filter((item) =>
                      tableSearch ? item.text.toLowerCase().includes(tableSearch.toLowerCase()) : true
                    )
                    .map((item) => {
                      const isChecked = selectedTableRows.includes(item.id)
                      return (
                        <tr
                          key={item.id}
                          className="hover:bg-slate-50/80 dark:hover:bg-white/[0.02] transition-colors group"
                        >
                          <td className="py-3 px-3">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {
                                setSelectedTableRows((prev) =>
                                  prev.includes(item.id)
                                    ? prev.filter((id) => id !== item.id)
                                    : [...prev, item.id]
                                )
                              }}
                              className="rounded accent-indigo-600 cursor-pointer"
                            />
                          </td>
                          <td className="py-3 px-3 max-w-[220px]">
                            <p className="font-semibold text-slate-900 dark:text-white truncate" title={item.text}>
                              {item.text}
                            </p>
                          </td>
                          <td className="py-3 px-3">
                            <span className="text-slate-700 dark:text-white/80">{item.voiceName}</span>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-600 dark:text-white/60">
                            {item.text.length}
                          </td>
                          <td className="py-3 px-3 font-mono text-[#F59E0B] font-semibold">
                            {item.isPreview ? '0' : item.text.length}
                          </td>
                          <td className="py-3 px-3 font-mono text-emerald-600 dark:text-emerald-400 font-medium">MP3</td>
                          <td className="py-3 px-3 text-slate-500 dark:text-white/40 font-mono text-[11px]">
                            {item.timestamp instanceof Date ? item.timestamp.toLocaleTimeString('vi-VN') : String(item.timestamp)}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleReplayItem(item)}
                                className="p-1.5 rounded-control text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-white/60 dark:hover:text-white dark:hover:bg-white/10"
                                title="Phát lại & nạp cài đặt"
                              >
                                <Play className="w-3.5 h-3.5 fill-current" />
                              </button>
                              <button
                                onClick={() => handleDownload(item.url, item.voiceId)}
                                className="p-1.5 rounded-control text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-white/60 dark:hover:text-white dark:hover:bg-white/10"
                                title="Tải về"
                              >
                                <Download className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* =========================================================================
          CỘT PHẢI (320px, THU GỌN ĐƯỢC): TAB "CÀI ĐẶT" & TAB "LỊCH SỬ"
      ========================================================================= */}
      <div
        className={`hidden lg:flex flex-col transition-all duration-150 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs overflow-hidden flex-shrink-0 ${
          rightPanelOpen ? 'w-[320px]' : 'w-12'
        }`}
      >
        {/* Header panel bên phải với nút toggle thu gọn */}
        <div className="p-3 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-50/70 dark:bg-[#0B0D12]/40">
          {rightPanelOpen ? (
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08] text-xs font-semibold w-full mr-2">
              <button
                onClick={() => setRightPanelTab('settings')}
                className={`flex-1 py-1 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'settings'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Sliders className="w-3 h-3" />
                <span>Cài đặt</span>
              </button>

              <button
                onClick={() => setRightPanelTab('history')}
                className={`flex-1 py-1 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'history'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-white/40 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <History className="w-3 h-3" />
                <span>Lịch sử ({history.length})</span>
              </button>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </div>
          )}

          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            title={rightPanelOpen ? 'Thu gọn panel' : 'Mở rộng panel'}
          >
            {rightPanelOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Nội dung Tab khi mở rộng */}
        {rightPanelOpen && (
          <div className="p-4 flex-1 overflow-y-auto space-y-6 scrollbar-thin">
            {rightPanelTab === 'settings' ? (
              /* TAB 1: CÀI ĐẶT */
              <div className="space-y-5">
                {/* 1. Bộ chọn giọng đọc */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider block">
                    Giọng đọc hiện tại
                  </label>
                  <div
                    onClick={() => setIsVoicePickerOpen(true)}
                    className="p-3 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#202532] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 cursor-pointer transition-all group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs flex-shrink-0">
                        {selectedVoice?.gender === 'Female' ? '♀' : '♂'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-slate-900 dark:text-white truncate">{selectedVoiceName}</p>
                        <p className="text-[10px] text-slate-500 dark:text-white/40 truncate">
                          {selectedVoice?.locale_name || 'Tiếng Việt'}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 dark:text-white/40 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                  </div>
                </div>

                {/* 2. Thanh trượt âm thanh */}
                <div className="space-y-4 pt-2 border-t border-slate-100 dark:border-white/[0.06]">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider">
                      Tinh chỉnh âm thanh
                    </span>
                    <button
                      onClick={handleResetSliders}
                      className="text-[11px] text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 flex items-center gap-1 font-medium"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Đặt lại</span>
                    </button>
                  </div>

                  {/* Tốc độ */}
                  <SliderControl
                    label="Tốc độ (Speed)"
                    value={rate}
                    min={-50}
                    max={100}
                    step={5}
                    displayValue={`${(1 + rate / 100).toFixed(1)}x (${rate >= 0 ? '+' : ''}${rate}%)`}
                    scaleLabels={['Chậm (0.5x)', 'Chuẩn (1.0x)', 'Nhanh (2.0x)']}
                    onChange={setRate}
                  />

                  {/* Cao độ */}
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

                  {/* Âm lượng */}
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

                {/* 3. Định dạng đầu ra */}
                <div className="pt-2 border-t border-slate-100 dark:border-white/[0.06] space-y-2">
                  <label className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider block">
                    Định dạng đầu ra
                  </label>
                  <div className="p-3 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-white">Audio MP3</p>
                      <p className="text-[10px] text-slate-500 dark:text-white/40">24kHz &middot; Mono &middot; 48kbps</p>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold border border-emerald-500/20">
                      Chuẩn
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              /* TAB 2: LỊCH SỬ PHIÊN */
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider">
                    Các bản ghi gần đây
                  </span>
                  {history.length > 0 && (
                    <button
                      onClick={clearHistory}
                      className="text-[11px] text-red-500 hover:text-red-600 dark:text-red-400 font-medium"
                    >
                      Xóa tất cả
                    </button>
                  )}
                </div>

                {history.length === 0 ? (
                  <p className="text-xs text-slate-400 dark:text-white/40 text-center py-8">
                    Chưa có bản ghi nào trong phiên hiện tại.
                  </p>
                ) : (
                  history.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleReplayItem(item)}
                      className="p-3 rounded-control bg-slate-50 hover:bg-slate-100 dark:bg-[#181C25] dark:hover:bg-[#1e232f] border border-slate-200 dark:border-white/[0.06] cursor-pointer transition-colors space-y-2 group"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-900 dark:text-white/90 truncate max-w-[180px]">
                          {item.voiceName}
                        </span>
                        <span className="text-slate-500 dark:text-white/40 font-mono text-[10px]">
                          {item.timestamp instanceof Date ? item.timestamp.toLocaleTimeString('vi-VN') : String(item.timestamp)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-white/60 line-clamp-2 leading-relaxed">
                        {item.text}
                      </p>
                      <div className="flex items-center justify-between pt-1 text-[10px] text-indigo-600 dark:text-indigo-400 group-hover:underline font-medium">
                        <span>Bấm để nạp lại cài đặt</span>
                        <Play className="w-3 h-3 fill-current" />
                      </div>
                    </div>
                  ))
                )}
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
                displayValue={`${(1 + rate / 100).toFixed(1)}x (${rate >= 0 ? '+' : ''}${rate}%)`}
                scaleLabels={['Chậm (0.5x)', 'Chuẩn (1.0x)', 'Nhanh (2.0x)']}
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
    </div>
  )
}
