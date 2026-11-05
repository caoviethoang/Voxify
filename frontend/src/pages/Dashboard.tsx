import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { fetchDashboardStats, type DashboardStats } from '../api/dashboard'
import { type HistoryItem } from '../api/history'
import {
  Mic,
  FileText,
  Volume2,
  Clock,
  Coins,
  Play,
  Pause,
  History,
  Sparkles,
  ArrowRight,
  BookOpen,
  Layers,
  Wand2,
  FileAudio,
  Radio,
  Plus,
  RotateCcw,
  Loader2,
} from 'lucide-react'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatTotalDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0 giây'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours} giờ ${minutes} phút`
  }
  if (minutes > 0) {
    return `${minutes} phút ${secs > 0 ? `${secs}s` : ''}`
  }
  return `${secs} giây`
}

function formatRelativeTime(dateStr?: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  if (diffSecs < 60) return 'vừa xong'
  const diffMins = Math.floor(diffSecs / 60)
  if (diffMins < 60) return `${diffMins} phút trước`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} giờ trước`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays} ngày trước`
  return date.toLocaleDateString('vi-VN')
}

// ─── Mini Audio Player Component ──────────────────────────────────────────────

function MiniAudioPlayer({ audioUrl, duration }: { audioUrl: string; duration: number }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [audioDuration, setAudioDuration] = useState(duration)
  const audioRef = useRef<HTMLAudioElement>(null)

  const toggle = () => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play().catch(() => {})
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return
    const val = Number(e.target.value)
    setCurrentTime(val)
    audio.currentTime = val
  }

  const progressPercent =
    audioDuration > 0 ? Math.min(100, Math.max(0, (currentTime / audioDuration) * 100)) : 0

  return (
    <div className="bg-slate-50 dark:bg-black/30 rounded-control p-3 border border-slate-200/60 dark:border-white/5 flex items-center gap-3">
      <audio
        ref={audioRef}
        src={audioUrl}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          setIsPlaying(false)
          setCurrentTime(0)
        }}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => {
          if (audioRef.current?.duration) {
            setAudioDuration(audioRef.current.duration)
          }
        }}
        preload="metadata"
      />
      <button
        onClick={toggle}
        className="w-8 h-8 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white flex items-center justify-center shrink-0 shadow-sm transition-transform active:scale-95 cursor-pointer"
        title={isPlaying ? 'Tạm dừng' : 'Phát'}
      >
        {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current ml-0.5" />}
      </button>

      <span className="text-[11px] font-mono text-slate-500 dark:text-white/50 shrink-0">
        {formatDuration(currentTime)}
      </span>

      <div className="flex-1 flex items-center relative">
        <input
          type="range"
          min={0}
          max={audioDuration || 100}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
          style={{ '--val': `${progressPercent}%` } as React.CSSProperties}
          className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />
      </div>

      <span className="text-[11px] font-mono text-slate-500 dark:text-white/50 shrink-0">
        {formatDuration(audioDuration)}
      </span>
    </div>
  )
}

// ─── Main Dashboard Component ─────────────────────────────────────────────────

export default function Dashboard() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDashboardStats()
      setStats(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Không thể tải dữ liệu bảng điều khiển'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  // Lời chào theo thời gian trong ngày
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 12) return t('greetings.morning') || 'Chào buổi sáng'
    if (hour >= 12 && hour < 18) return t('greetings.afternoon') || 'Chào buổi chiều'
    if (hour >= 18 && hour < 22) return t('greetings.evening') || 'Chào buổi tối'
    return 'Chào đêm muộn'
  }

  const userName = user?.full_name || user?.email.split('@')[0] || 'bạn'
  const userBalance = user?.credits ?? stats?.credit_balance ?? 0

  const handleReopen = (item: HistoryItem) => {
    navigate('/tts', { state: { reopenJob: item } })
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* ── 1. Header Greeting & Credit Chip ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>
              {getGreeting()}, {userName}
            </span>
            <span className="inline-block animate-bounce">👋</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1">
            Chào mừng bạn trở lại với không gian sáng tạo giọng nói và nội dung AI của Voxify.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Chip số dư credit */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400">
            <Coins className="w-4 h-4 text-amber-500 shrink-0" />
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase font-semibold text-amber-600 dark:text-amber-400/80">
                Số dư:
              </span>
              <span className="text-xs font-mono font-bold text-amber-900 dark:text-amber-300">
                {userBalance.toLocaleString('vi-VN')}
              </span>
            </div>
            <Link
              to="/credits"
              className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500 hover:bg-amber-600 text-white transition-colors"
              title="Nạp thêm credit"
            >
              <Plus className="w-3 h-3" />
              <span>Nạp thêm</span>
            </Link>
          </div>

          {/* Nút hành động nhanh */}
          <Link
            to="/studio"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all"
          >
            <Mic className="w-4 h-4" />
            <span>Tạo giọng nói</span>
          </Link>
        </div>
      </div>

      {/* ── 2. Thống kê tổng quan (4 KPI Cards) ──────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Ký tự tháng này */}
        <div className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-white/50">
              Ký tự tháng này
            </span>
            <div className="w-8 h-8 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold font-mono text-slate-900 dark:text-white">
            {loading ? '...' : (stats?.chars_used_this_month ?? 0).toLocaleString('vi-VN')}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-white/40 mt-1">Đã dùng trong tháng</p>
        </div>

        {/* Audio đã tạo */}
        <div className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-white/50">
              Audio đã tạo
            </span>
            <div className="w-8 h-8 rounded-control bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <Volume2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold font-mono text-slate-900 dark:text-white">
            {loading ? '...' : stats?.total_audio_generated ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-white/40 mt-1">Tác vụ thành công</p>
        </div>

        {/* Tổng thời lượng */}
        <div className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-white/50">
              Tổng thời lượng
            </span>
            <div className="w-8 h-8 rounded-control bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-lg sm:text-2xl font-extrabold font-mono text-slate-900 dark:text-white truncate">
            {loading ? '...' : formatTotalDuration(stats?.total_duration_seconds ?? 0)}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-white/40 mt-1">Tổng âm thanh đã tạo</p>
        </div>

        {/* Số dư credit */}
        <div className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-white/50">
              Credit khả dụng
            </span>
            <div className="w-8 h-8 rounded-control bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Coins className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold font-mono text-amber-600 dark:text-amber-400">
            {loading ? '...' : userBalance.toLocaleString('vi-VN')}
          </div>
          <Link
            to="/credits"
            className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline mt-1 inline-block font-medium"
          >
            Lịch sử giao dịch &rarr;
          </Link>
        </div>
      </div>

      {/* ── 3. Row 1: Thẻ lớn "Tiếp tục công việc" + Cột "Tạo nhanh" ─────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Thẻ lớn "Tiếp tục công việc" (col-span-7) */}
        <div className="lg:col-span-7 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
                Tiếp tục công việc
              </span>
              {stats?.latest_generation && (
                <span className="text-[10px] text-indigo-700 dark:text-indigo-400 font-semibold bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200/60 dark:border-indigo-500/20 px-2 py-0.5 rounded-full uppercase">
                  {stats.latest_generation.format || 'MP3'}
                </span>
              )}
            </div>

            {loading ? (
              <div className="py-8 flex flex-col items-center justify-center text-slate-400 dark:text-white/40 gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                <span className="text-xs">Đang tải tác vụ gần nhất...</span>
              </div>
            ) : stats?.latest_generation ? (
              <div>
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 rounded-control bg-indigo-50 dark:bg-white/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                    <Mic className="w-5 h-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white/90 line-clamp-2 leading-snug">
                      {stats.latest_generation.title || stats.latest_generation.text}
                    </h3>
                    <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-white/40 mt-1 flex-wrap">
                      <span>Giọng: {stats.latest_generation.voice}</span>
                      <span>&middot;</span>
                      <span>{formatDuration(stats.latest_generation.duration)}</span>
                      <span>&middot;</span>
                      <span>{formatRelativeTime(stats.latest_generation.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Real Mini Audio Player */}
                {stats.latest_generation.audio_url ? (
                  <MiniAudioPlayer
                    audioUrl={stats.latest_generation.audio_url}
                    duration={stats.latest_generation.duration}
                  />
                ) : (
                  <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-control border border-slate-200/60 dark:border-white/5 text-xs text-slate-500 dark:text-white/40">
                    Tác vụ đang xử lý hoặc không có tệp audio khả dụng.
                  </div>
                )}
              </div>
            ) : (
              /* Trạng thái rỗng cho người dùng mới */
              <div className="py-6 px-4 text-center flex flex-col items-center justify-center rounded-control bg-slate-50/60 dark:bg-white/[0.02] border border-dashed border-slate-200 dark:border-white/10">
                <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">
                  Bắt đầu tạo audio đầu tiên của bạn
                </h3>
                <p className="text-xs text-slate-500 dark:text-white/50 max-w-md mt-1 mb-4 leading-relaxed">
                  Chuyển văn bản thành giọng đọc truyền cảm, chất lượng phòng thu với hàng trăm giọng đọc AI tiếng Việt đa dạng.
                </p>
                <Link
                  to="/studio"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-control bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Tạo bản ghi mới</span>
                </Link>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 mt-5 pt-4 border-t border-slate-100 dark:border-white/5">
            {stats?.latest_generation && (
              <button
                onClick={() => handleReopen(stats.latest_generation!)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-control bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-500/10 dark:hover:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400 text-xs font-semibold transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Mở lại trong Studio</span>
              </button>
            )}

            <Link
              to="/history"
              className="px-4 py-2 rounded-control border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-slate-700 dark:text-white/70 text-xs font-semibold transition-colors"
            >
              Xem lịch sử
            </Link>
          </div>
        </div>

        {/* Cột "Tạo nhanh" (col-span-5) */}
        <div className="lg:col-span-5 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
                Tạo nhanh
              </span>
              <span className="text-[10px] text-slate-400 dark:text-white/30 font-mono">
                Công cụ AI
              </span>
            </div>

            <div className="space-y-3">
              {/* Option 1: Text to Speech */}
              <Link
                to="/studio"
                className="p-3 rounded-control border border-slate-200 dark:border-white/10 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-white/5 transition-all flex items-center justify-between group block"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                    <Mic className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        Tạo audio từ văn bản
                      </h4>
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold border border-indigo-500/20">
                        HOT
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-white/50 mt-0.5">
                      Chuyển văn bản thành giọng nói tự nhiên, đa ngữ điệu
                    </p>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 group-hover:translate-x-0.5 transition-all" />
              </Link>

              {/* Option 2: Speech to Text (Sắp ra mắt) */}
              <div className="p-3 rounded-control border border-slate-200/60 dark:border-white/[0.06] bg-slate-50/50 dark:bg-white/[0.02] opacity-75 flex items-center justify-between cursor-not-allowed">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-control bg-slate-200/60 dark:bg-white/5 text-slate-500 dark:text-white/40 flex items-center justify-center shrink-0">
                    <FileAudio className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h4 className="text-xs font-bold text-slate-700 dark:text-white/70">
                        Speech to Text
                      </h4>
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-white/40 font-bold">
                        Sắp ra mắt
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 dark:text-white/30 mt-0.5">
                      Ghi âm và nhận diện giọng nói tiếng Việt thành văn bản
                    </p>
                  </div>
                </div>
              </div>

              {/* Option 3: Voice Cloning (Sắp ra mắt) */}
              <div className="p-3 rounded-control border border-slate-200/60 dark:border-white/[0.06] bg-slate-50/50 dark:bg-white/[0.02] opacity-75 flex items-center justify-between cursor-not-allowed">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-control bg-slate-200/60 dark:bg-white/5 text-slate-500 dark:text-white/40 flex items-center justify-center shrink-0">
                    <Wand2 className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h4 className="text-xs font-bold text-slate-700 dark:text-white/70">
                        Clone giọng nói
                      </h4>
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-white/40 font-bold">
                        Sắp ra mắt
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 dark:text-white/30 mt-0.5">
                      Tạo bản sao giọng nói độc quyền từ mẫu âm thanh ngắn
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 text-center">
            <Link
              to="/voices"
              className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
            >
              <span>Xem 300+ giọng đọc trong Thư viện</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* ── 4. Row 2: Khám phá tính năng + Hoạt động gần đây ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Khám phá tính năng (col-span-8) */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
              Khám phá tính năng
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            {/* 1. Studio Text to Speech */}
            <Link
              to="/studio"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Mic className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Studio TTS</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 font-bold">
                    HOT
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Soạn thảo kịch bản, chỉnh tốc độ, cao độ, chèn ngắt nghỉ và xuất phụ đề SRT/VTT.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Khám phá &rarr;
              </span>
            </Link>

            {/* 2. Thư viện giọng đọc */}
            <Link
              to="/voices"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Radio className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Thư viện giọng</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold">
                    HOT
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Khám phá hơn 300+ giọng đọc nam nữ, vùng miền Bắc - Trung - Nam và quốc tế.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Xem thư viện &rarr;
              </span>
            </Link>

            {/* 3. Lịch sử xử lý */}
            <Link
              to="/history"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-purple-50 text-purple-600 dark:bg-purple-500/10 dark:text-purple-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <History className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Lịch sử xử lý</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 font-bold">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Quản lý, nghe lại, tải audio, tải phụ đề SRT/VTT và tải ZIP hàng loạt.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Vào lịch sử &rarr;
              </span>
            </Link>

            {/* 4. Sổ cái & Credit */}
            <Link
              to="/credits"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Coins className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Lịch sử Credit</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-bold">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Theo dõi sổ cái biến động credit chi tiết từng lần tạo và hoàn trả tự động.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Xem chi tiết &rarr;
              </span>
            </Link>

            {/* 5. Từ điển phát âm */}
            <Link
              to="/studio"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Từ điển phát âm</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-bold">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Quy tắc thay thế từ viết tắt, địa danh, tên riêng trước khi chuyển giọng nói.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Mở từ điển &rarr;
              </span>
            </Link>

            {/* 6. Kịch bản đa giọng */}
            <Link
              to="/studio"
              className="bg-white dark:bg-[#12151C] rounded-card p-4 border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/50 hover:shadow-sm transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Layers className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Kịch bản đa giọng</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 font-bold">
                    HOT
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1 line-clamp-2">
                  Tạo đoạn hội thoại podcast, kịch nhiều nhân vật trong cùng một file audio duy nhất.
                </p>
              </div>
              <span className="mt-3 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 inline-flex items-center gap-1">
                Thử ngay &rarr;
              </span>
            </Link>
          </div>
        </div>

        {/* Hoạt động gần đây (col-span-4) */}
        <div className="lg:col-span-4 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
                Hoạt động gần đây
              </span>
              <span className="text-[11px] text-slate-400 dark:text-white/30 font-mono">
                {stats?.recent_activities.length ?? 0} mục
              </span>
            </div>

            {loading ? (
              <div className="py-8 flex flex-col items-center justify-center text-slate-400 dark:text-white/40 gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                <span className="text-xs">Đang tải hoạt động...</span>
              </div>
            ) : error ? (
              <div className="p-3 bg-rose-50 dark:bg-rose-500/10 rounded-control border border-rose-200 dark:border-rose-500/20 text-xs text-rose-600 dark:text-rose-400">
                {error}
              </div>
            ) : stats?.recent_activities && stats.recent_activities.length > 0 ? (
              <div className="space-y-2.5">
                {stats.recent_activities.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleReopen(item)}
                    className="p-2.5 rounded-control hover:bg-slate-50 dark:hover:bg-white/5 border border-transparent hover:border-slate-200 dark:hover:border-white/10 transition-all flex items-center gap-3 cursor-pointer group"
                    title="Bấm để mở lại trong Studio"
                  >
                    <div className="w-8 h-8 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                      <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {item.title || item.text}
                      </p>
                      <p className="text-[10px] text-slate-500 dark:text-white/40 mt-0.5">
                        Text to Speech &middot; {formatDuration(item.duration)} &middot; {formatRelativeTime(item.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-slate-400 dark:text-white/40">
                <p className="text-xs">Chưa có hoạt động nào gần đây.</p>
                <Link
                  to="/studio"
                  className="text-xs text-indigo-600 dark:text-indigo-400 font-medium hover:underline mt-1 inline-block"
                >
                  Tạo bản ghi đầu tiên
                </Link>
              </div>
            )}
          </div>

          <Link
            to="/history"
            className="w-full mt-4 py-2 rounded-control border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-center text-xs font-semibold text-slate-700 dark:text-white/70 block transition-colors"
          >
            Xem tất cả lịch sử &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
