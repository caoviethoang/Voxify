import { useState, useCallback, useEffect, useRef } from 'react'
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
  const { config } = useAppConfig()
  const { data: voiceData } = useVoices()
  const { isLoading, error, currentUrl, history, generate, clearHistory, setError } = useTTS()
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

  // Tổng hợp giọng nói
  const handleSynthesize = useCallback(
    async (isPreview: boolean) => {
      if (!text.trim()) {
        toast.error('Vui lòng nhập văn bản trước khi tạo giọng nói.')
        return
      }
      if (!selectedVoiceId) {
        toast.error('Vui lòng chọn một giọng đọc.')
        return
      }
      if (!isPreview && text.length > config.max_chars) {
        toast.error(`Văn bản vượt quá ${config.max_chars.toLocaleString('vi-VN')} ký tự.`)
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
        toast.success(
          isPreview ? 'Nghe thử 200 ký tự hoàn tất!' : 'Đã tạo giọng nói thành công!'
        )
      }
    },
    [text, selectedVoiceId, config.max_chars, generate, rateStr, pitchStr, volumeStr, selectedVoiceName, toast]
  )

  // Phím tắt ⌘+Enter / Ctrl+Enter để tạo giọng nói
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        if (!isLoading) {
          handleSynthesize(false)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSynthesize, isLoading])

  useEffect(() => {
    if (error) {
      toast.error(error)
      setError(null)
    }
  }, [error, toast, setError])

  const activeUrl = replayUrl ?? currentUrl
  const activeVoiceName = replayVoice || selectedVoiceName
  const activeIsPreview = replayUrl ? replayIsPreview : (history[0]?.isPreview ?? false)

  // Tải file audio
  const handleDownload = (url: string | null, voiceId: string) => {
    if (!url) {
      toast.error('Chưa có bản ghi âm để tải về.')
      return
    }
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const filename = `voxify_${voiceId}_${timestamp}.mp3`
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  // Chèn khoảng ngắt nghỉ vào con trỏ chuột trong textarea
  const insertPause = (ms: number = 500) => {
    if (!textareaRef.current) return
    const el = textareaRef.current
    const start = el.selectionStart
    const end = el.selectionEnd
    const pauseTag = ` ... `
    const newText = text.substring(0, start) + pauseTag + text.substring(end)
    setText(newText)
    setTimeout(() => {
      el.focus()
      el.setSelectionRange(start + pauseTag.length, start + pauseTag.length)
    }, 10)
    toast.info(`Đã chèn ngắt nghỉ (${ms}ms)`)
  }

  // Đặt lại các thanh trượt
  const handleResetSliders = () => {
    setRate(0)
    setPitch(0)
    setVolume(0)
    toast.info('Đã đặt lại thông số âm thanh về mặc định.')
  }

  // Nạp lại dữ liệu từ lịch sử
  const handleReplayItem = (item: any) => {
    setReplayUrl(item.url)
    setReplayVoice(item.voiceName)
    setReplayIsPreview(item.isPreview)
    setText(item.text)
    setSelectedVoiceId(item.voiceId)
    toast.info('Đã tải lại nội dung và giọng đọc vào Studio.')
  }

  // Ước tính số credit tiêu tốn (1 ký tự = 1 credit)
  const estimatedCredits = text.trim().length

  return (
    <div className="flex flex-col lg:flex-row gap-5 max-w-[1600px] mx-auto min-h-[calc(100vh-100px)]">
      {/* =========================================================================
          CỘT CHÍNH (GIỮA): TOOLBAR + Ô SOẠN THẢO + ACTION BAR + BẢNG CHUYỂN ĐỔI
      ========================================================================= */}
      <div className="flex-1 flex flex-col min-w-0 space-y-6">
        {/* Editor Box */}
        <div className="rounded-card bg-[#12151C] dark:bg-[#12151C] bg-white border border-white/[0.08] dark:border-white/[0.08] border-slate-200 shadow-sm flex flex-col overflow-hidden">
          {/* 1. Thanh công cụ phía trên ô soạn thảo */}
          <div className="p-3 border-b border-white/[0.08] dark:border-white/[0.08] border-slate-100 bg-[#0B0D12]/40 dark:bg-[#0B0D12]/40 bg-slate-50 flex flex-wrap items-center justify-between gap-2">
            {/* Giọng đang chọn + Tốc độ + Định dạng */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Chip giọng đọc đang chọn */}
              <button
                onClick={() => setIsVoicePickerOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-[#181C25] dark:bg-[#181C25] bg-white border border-white/[0.1] hover:border-indigo-500/50 text-xs font-semibold text-white transition-all shadow-sm"
              >
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                <span className="truncate max-w-[140px]">{selectedVoiceName}</span>
                <span className="text-[10px] text-indigo-400 font-mono">Đổi giọng &rarr;</span>
              </button>

              {/* Chip Tốc độ */}
              <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-control bg-[#181C25] text-xs text-white/70 font-mono">
                <span className="text-[10px] text-white/40">Tốc độ:</span>
                <span>{rateStr}</span>
              </div>

              {/* Định dạng */}
              <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-control bg-[#181C25] text-xs text-white/70 font-mono">
                <span className="text-[10px] text-white/40">Định dạng:</span>
                <span className="text-emerald-400 font-semibold">MP3</span>
              </div>
            </div>

            {/* Các tiện ích: Ngắt nghỉ, Từ điển, Nút mở Cài đặt mobile */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => insertPause(500)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-control hover:bg-white/5 text-xs text-white/70 hover:text-white transition-colors"
                title="Chèn dấu ngắt nghỉ tại vị trí con trỏ"
              >
                <PauseCircle className="w-3.5 h-3.5 text-indigo-400" />
                <span className="hidden sm:inline">Ngắt nghỉ</span>
              </button>

              <button
                onClick={() => toast.info('Tính năng Từ điển phát âm sẽ ra mắt ở phiên bản tiếp theo.')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-control hover:bg-white/5 text-xs text-white/70 hover:text-white transition-colors"
                title="Từ điển phát âm"
              >
                <BookA className="w-3.5 h-3.5 text-indigo-400" />
                <span className="hidden sm:inline">Từ điển</span>
              </button>

              {/* Nút mở Settings panel trên tablet/mobile */}
              <button
                onClick={() => setMobileDrawerOpen(true)}
                className="lg:hidden flex items-center gap-1 px-2.5 py-1.5 rounded-control bg-[#181C25] text-xs text-white"
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
              className="w-full bg-transparent text-sm sm:text-base leading-relaxed text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/20 focus:outline-none resize-none font-sans"
            />

            {/* Hàng chip ví dụ khi ô trống */}
            {!text.trim() && (
              <div className="pt-2 border-t border-white/[0.04]">
                <span className="text-[11px] text-white/30 block mb-2 font-medium">
                  Ví dụ mẫu (bấm để thử ngay):
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {SAMPLE_PROMPTS.map((sample) => {
                    const Icon = sample.icon
                    return (
                      <button
                        key={sample.id}
                        onClick={() => setText(sample.text)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-[#181C25] hover:bg-[#1f2430] border border-white/[0.06] hover:border-indigo-500/40 text-xs text-white/80 hover:text-white transition-all group"
                      >
                        <Icon className="w-3.5 h-3.5 text-indigo-400 group-hover:scale-110 transition-transform" />
                        <span>{sample.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* 3. Thanh hành động cố định phía dưới */}
          <div className="p-3.5 border-t border-white/[0.08] dark:border-white/[0.08] border-slate-100 bg-[#0B0D12]/70 dark:bg-[#0B0D12]/70 bg-slate-50 flex flex-wrap items-center justify-between gap-3">
            {/* Đếm ký tự & Credit ước tính */}
            <div className="flex items-center gap-3 text-xs">
              {/* Đếm ký tự */}
              <div className="font-mono text-slate-500 dark:text-white/50">
                <span className="text-white font-semibold">{text.length.toLocaleString('vi-VN')}</span>
                <span> / {config.max_chars?.toLocaleString('vi-VN') || '20.000'} ký tự</span>
              </div>

              {/* Ước tính credit tiêu tốn */}
              {estimatedCredits > 0 && (
                <div className="flex items-center gap-1 text-[11px] font-mono text-[#F59E0B] bg-[#F59E0B]/10 px-2 py-0.5 rounded">
                  <Coins className="w-3 h-3" />
                  <span>~{estimatedCredits.toLocaleString('vi-VN')} credit</span>
                </div>
              )}
            </div>

            {/* Các nút hành động chính */}
            <div className="flex items-center gap-2.5">
              {/* Nút Nghe thử */}
              <button
                type="button"
                onClick={() => handleSynthesize(true)}
                disabled={isLoading || !text.trim()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-control border border-white/[0.1] hover:border-white/[0.2] hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-white transition-all"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Nghe thử (200 ký tự)</span>
              </button>

              {/* Nút Tạo giọng nói chính: Gradient Chàm -> Tím */}
              <button
                type="button"
                onClick={() => handleSynthesize(false)}
                disabled={isLoading || !text.trim()}
                className="flex items-center gap-2 px-5 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all"
                title="Phím tắt: ⌘+Enter / Ctrl+Enter"
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
                    <span className="hidden sm:inline-block font-mono text-[10px] text-white/50 bg-white/10 px-1 py-0.2 rounded">
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
        <div className="rounded-card bg-[#12151C] dark:bg-[#12151C] bg-white border border-white/[0.08] dark:border-white/[0.08] border-slate-200 shadow-sm p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Danh sách chuyển đổi
              </h3>
              <p className="text-[11px] text-slate-400 dark:text-white/40">
                Toàn bộ các bản ghi giọng nói đã thực hiện trong phiên làm việc
              </p>
            </div>

            {/* Thanh công cụ bảng: Search + Refresh */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-white/30 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  placeholder="Tìm kiếm bản ghi..."
                  className="bg-[#181C25] border border-white/[0.08] rounded-control pl-7 pr-3 py-1 text-xs text-white placeholder:text-white/30 focus:outline-none"
                />
              </div>

              <button
                onClick={() => toast.info('Đã làm mới danh sách')}
                className="p-1.5 rounded-control text-white/40 hover:text-white hover:bg-white/5 border border-white/[0.08]"
                title="Làm mới"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-white/40 border-b border-white/[0.06] bg-[#0B0D12]/30">
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
              <tbody className="divide-y divide-white/[0.04]">
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-white/30">
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
                          className="hover:bg-white/[0.02] transition-colors group"
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
                            <p className="font-medium text-white truncate" title={item.text}>
                              {item.text}
                            </p>
                          </td>
                          <td className="py-3 px-3">
                            <span className="text-white/80">{item.voiceName}</span>
                          </td>
                          <td className="py-3 px-3 font-mono text-white/60">
                            {item.text.length}
                          </td>
                          <td className="py-3 px-3 font-mono text-[#F59E0B] font-semibold">
                            {item.isPreview ? '0' : item.text.length}
                          </td>
                          <td className="py-3 px-3 font-mono text-emerald-400">MP3</td>
                          <td className="py-3 px-3 text-white/40 font-mono text-[11px]">
                            {item.timestamp instanceof Date ? item.timestamp.toLocaleTimeString('vi-VN') : String(item.timestamp)}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleReplayItem(item)}
                                className="p-1.5 rounded text-white/60 hover:text-white hover:bg-white/10"
                                title="Phát lại & nạp cài đặt"
                              >
                                <Play className="w-3.5 h-3.5 fill-current" />
                              </button>
                              <button
                                onClick={() => handleDownload(item.url, item.voiceId)}
                                className="p-1.5 rounded text-white/60 hover:text-white hover:bg-white/10"
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
        className={`hidden lg:flex flex-col transition-all duration-150 rounded-card bg-[#12151C] dark:bg-[#12151C] bg-white border border-white/[0.08] dark:border-white/[0.08] border-slate-200 shadow-sm overflow-hidden flex-shrink-0 ${
          rightPanelOpen ? 'w-[320px]' : 'w-12'
        }`}
      >
        {/* Header panel bên phải với nút toggle thu gọn */}
        <div className="p-3 border-b border-white/[0.08] flex items-center justify-between bg-[#0B0D12]/40">
          {rightPanelOpen ? (
            <div className="flex items-center gap-1 bg-[#181C25] p-0.5 rounded-control border border-white/[0.08] text-xs font-semibold w-full mr-2">
              <button
                onClick={() => setRightPanelTab('settings')}
                className={`flex-1 py-1 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'settings'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                    : 'text-white/40 hover:text-white'
                }`}
              >
                <Sliders className="w-3 h-3" />
                <span>Cài đặt</span>
              </button>

              <button
                onClick={() => setRightPanelTab('history')}
                className={`flex-1 py-1 rounded-[8px] transition-all flex items-center justify-center gap-1.5 ${
                  rightPanelTab === 'history'
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                    : 'text-white/40 hover:text-white'
                }`}
              >
                <History className="w-3 h-3" />
                <span>Lịch sử ({history.length})</span>
              </button>
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <Sliders className="w-4 h-4 text-indigo-400" />
            </div>
          )}

          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="p-1 rounded text-white/40 hover:text-white hover:bg-white/5 transition-colors"
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
                  <label className="text-xs font-bold text-white uppercase tracking-wider block">
                    Giọng đọc hiện tại
                  </label>
                  <div
                    onClick={() => setIsVoicePickerOpen(true)}
                    className="p-3 rounded-control bg-[#181C25] border border-white/[0.08] hover:border-indigo-500/50 cursor-pointer transition-all group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-bold text-xs flex-shrink-0">
                        {selectedVoice?.gender === 'Female' ? '♀' : '♂'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-white truncate">{selectedVoiceName}</p>
                        <p className="text-[10px] text-white/40 truncate">
                          {selectedVoice?.locale_name || 'Tiếng Việt'}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/40 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                  </div>
                </div>

                {/* 2. Thanh trượt âm thanh */}
                <div className="space-y-4 pt-2 border-t border-white/[0.06]">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Tinh chỉnh âm thanh
                    </span>
                    <button
                      onClick={handleResetSliders}
                      className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
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
                <div className="pt-2 border-t border-white/[0.06] space-y-2">
                  <label className="text-xs font-bold text-white uppercase tracking-wider block">
                    Định dạng đầu ra
                  </label>
                  <div className="p-3 rounded-control bg-[#181C25] border border-white/[0.08] flex items-center justify-between text-xs">
                    <div>
                      <p className="font-semibold text-white">Audio MP3</p>
                      <p className="text-[10px] text-white/40">24kHz &middot; Mono &middot; 48kbps</p>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                      Chuẩn
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              /* TAB 2: LỊCH SỬ PHIÊN */
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Các bản ghi gần đây
                  </span>
                  {history.length > 0 && (
                    <button
                      onClick={clearHistory}
                      className="text-[11px] text-red-400 hover:text-red-300"
                    >
                      Xóa tất cả
                    </button>
                  )}
                </div>

                {history.length === 0 ? (
                  <p className="text-xs text-white/40 text-center py-8">
                    Chưa có bản ghi nào trong phiên hiện tại.
                  </p>
                ) : (
                  history.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleReplayItem(item)}
                      className="p-3 rounded-control bg-[#181C25] hover:bg-[#1e232f] border border-white/[0.06] cursor-pointer transition-colors space-y-2 group"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-white/90 truncate max-w-[180px]">
                          {item.voiceName}
                        </span>
                        <span className="text-white/40 font-mono text-[10px]">
                          {item.timestamp instanceof Date ? item.timestamp.toLocaleTimeString('vi-VN') : String(item.timestamp)}
                        </span>
                      </div>
                      <p className="text-xs text-white/60 line-clamp-2 leading-relaxed">
                        {item.text}
                      </p>
                      <div className="flex items-center justify-between pt-1 text-[10px] text-indigo-400 group-hover:underline">
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
          <div className="fixed inset-y-0 right-0 max-w-sm w-full bg-[#12151C] p-5 shadow-2xl z-10 overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] mb-4">
              <h3 className="text-sm font-bold text-white">Cài đặt giọng nói</h3>
              <button
                onClick={() => setMobileDrawerOpen(false)}
                className="p-1 rounded text-white/40 hover:text-white"
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
          toast.success(`Đã chọn giọng đọc ${voices.find(v => v.id === id)?.name || id}`)
        }}
        onPreviewSample={(id) => {
          toast.info(`Đang nghe thử giọng ${voices.find(v => v.id === id)?.name || id}`)
        }}
      />
    </div>
  )
}
