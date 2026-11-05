import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import JSZip from 'jszip'
import {
  History as HistoryIcon,
  Search,
  RotateCcw,
  Trash2,
  Download,
  Play,
  Pause,
  FileText,
  ChevronLeft,
  ChevronRight,
  Coins,
  CheckSquare,
  Square,
  Pencil,
  Check,
  X,
  AlertCircle,
  RefreshCw,
  Archive,
  Loader2,
  Volume2,
  Subtitles,
  ExternalLink,
  Copy,
} from 'lucide-react'
import clsx from 'clsx'
import { useToast } from '../hooks/useToast'
import {
  historyApi,
  type HistoryItem,
  type HistoryListParams,
} from '../api/history'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatRelativeTime(dateStr: string): string {
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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

interface StatusBadgeProps {
  status: HistoryItem['status']
  progress: number
}

function StatusBadge({ status, progress }: StatusBadgeProps) {
  switch (status) {
    case 'done':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
          Thành công
        </span>
      )
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20">
          Thất bại
        </span>
      )
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
          <Loader2 className="w-3 h-3 animate-spin" />
          {progress}%
        </span>
      )
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-white/60 border border-slate-200 dark:border-white/10">
          Chờ xử lý
        </span>
      )
  }
}

// ─── Format Badge ─────────────────────────────────────────────────────────────

function FormatBadge({ format }: { format: string }) {
  const upper = format.toUpperCase()
  return (
    <span
      className={clsx(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wide border',
        upper === 'MP3'
          ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/20'
          : 'bg-purple-50 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400 border-purple-200 dark:border-purple-500/20'
      )}
    >
      {upper}
    </span>
  )
}

// ─── Skeleton Row ─────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100 dark:border-white/[0.05]">
      {[...Array(9)].map((_, i) => (
        <td key={i} className="py-3.5 px-4">
          <div className="h-4 rounded bg-slate-200 dark:bg-white/[0.07] animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
        </td>
      ))}
    </tr>
  )
}

// ─── Confirm Dialog ───────────────────────────────────────────────────────────

interface ConfirmDialogProps {
  message: string
  onConfirm: () => void
  onCancel: () => void
}

function ConfirmDialog({ message, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-card shadow-2xl border border-slate-200 dark:border-white/10 w-full max-w-sm mx-4 p-6">
        <div className="flex items-start gap-3 mb-5">
          <AlertCircle className="w-5 h-5 text-rose-500 mt-0.5 shrink-0" />
          <p className="text-slate-700 dark:text-white/80 text-sm leading-relaxed">{message}</p>
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3.5 py-1.5 text-sm rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
          >
            Hủy
          </button>
          <button
            onClick={onConfirm}
            className="px-3.5 py-1.5 text-sm rounded-control bg-rose-600 hover:bg-rose-700 text-white font-medium transition-colors"
          >
            Xóa
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Inline Title Editor ──────────────────────────────────────────────────────

interface TitleEditorProps {
  item: HistoryItem
  onSave: (id: number, title: string) => Promise<void>
}

function TitleEditor({ item, onSave }: TitleEditorProps) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.title)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const startEdit = () => {
    setValue(item.title)
    setEditing(true)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  const save = async () => {
    if (value.trim() === item.title || value.trim() === '') {
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onSave(item.id, value.trim())
    } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  const cancel = () => {
    setValue(item.title)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1 w-full">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') save()
            if (e.key === 'Escape') cancel()
          }}
          className="flex-1 min-w-0 text-sm px-2 py-0.5 rounded border border-indigo-400 dark:border-indigo-500 bg-white dark:bg-white/10 text-slate-900 dark:text-white outline-none"
          autoFocus
          disabled={saving}
        />
        <button
          onClick={save}
          disabled={saving}
          className="p-1 rounded text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 transition-colors"
          title="Lưu"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={cancel}
          className="p-1 rounded text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
          title="Hủy"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="group flex items-center gap-1.5 cursor-pointer" onDoubleClick={startEdit} title="Nhấn đúp để sửa tên">
      <span className="text-sm text-slate-700 dark:text-white/80 font-medium line-clamp-1 max-w-[200px]">
        {item.title || item.text.slice(0, 60)}
      </span>
      <button
        onClick={startEdit}
        className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-indigo-500 transition-all"
        title="Sửa tên"
      >
        <Pencil className="w-3 h-3" />
      </button>
    </div>
  )
}

// ─── Audio Player Row ─────────────────────────────────────────────────────────

function AudioPlayerRow({ audioUrl }: { audioUrl: string }) {
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const audioRef = useRef<HTMLAudioElement>(null)

  const toggle = () => {
    const audio = audioRef.current
    if (!audio) return
    if (playing) {
      audio.pause()
    } else {
      audio.play()
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = Number(e.target.value)
  }

  return (
    <div className="flex items-center gap-3 py-2 px-1">
      <audio
        ref={audioRef}
        src={audioUrl}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDuration(audioRef.current?.duration ?? 0)}
        preload="metadata"
      />
      <button
        onClick={toggle}
        className="shrink-0 w-7 h-7 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center transition-colors"
      >
        {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
      </button>
      <input
        type="range"
        min={0}
        max={duration || 100}
        value={currentTime}
        onChange={handleSeek}
        className="flex-1 h-1 accent-indigo-600 cursor-pointer"
      />
      <span className="text-[11px] font-mono text-slate-500 dark:text-white/40 shrink-0">
        {formatDuration(currentTime)} / {formatDuration(duration)}
      </span>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const LIMIT = 15

interface FilterState {
  search: string
  status: string
  format: string
  date_from: string
  date_to: string
}

const DEFAULT_FILTER: FilterState = {
  search: '',
  status: '',
  format: '',
  date_from: '',
  date_to: '',
}

interface PageState {
  items: HistoryItem[]
  total: number
  pages: number
}

interface ConfirmState {
  message: string
  onConfirm: () => void
}

export default function History() {
  const navigate = useNavigate()
  const toast = useToast()

  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pageData, setPageData] = useState<PageState>({ items: [], total: 0, pages: 1 })

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)
  const [bulkDownloading, setBulkDownloading] = useState(false)

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const load = useCallback(async (params: HistoryListParams) => {
    setLoading(true)
    setError(null)
    try {
      const res = await historyApi.list(params)
      setPageData({ items: res.items, total: res.total, pages: res.pages })
    } catch {
      setError('Không thể tải dữ liệu. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const params: HistoryListParams = {
      page,
      limit: LIMIT,
      ...(filter.search ? { search: filter.search } : {}),
      ...(filter.status ? { status: filter.status } : {}),
      ...(filter.format ? { format: filter.format } : {}),
      ...(filter.date_from ? { date_from: filter.date_from } : {}),
      ...(filter.date_to ? { date_to: filter.date_to } : {}),
    }
    load(params)
    setSelectedIds(new Set())
  }, [page, filter, load])

  // ── Filter handlers ────────────────────────────────────────────────────────

  const updateFilter = (key: keyof FilterState, value: string) => {
    setFilter((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const resetFilter = () => {
    setFilter(DEFAULT_FILTER)
    setPage(1)
  }

  // ── Selection ──────────────────────────────────────────────────────────────

  const isAllSelected =
    pageData.items.length > 0 && pageData.items.every((item) => selectedIds.has(item.id))

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(pageData.items.map((i) => i.id)))
    }
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // ── Delete ─────────────────────────────────────────────────────────────────

  const askDelete = (message: string, onConfirm: () => void) => {
    setConfirm({ message, onConfirm })
  }

  const handleDeleteOne = (id: number) => {
    askDelete('Bạn có chắc muốn xóa bản ghi này không?', async () => {
      setConfirm(null)
      await historyApi.deleteOne(id)
      load({ page, limit: LIMIT, ...buildFilterParams() })
      setSelectedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
    })
  }

  const handleDeleteBulk = () => {
    const ids = [...selectedIds]
    askDelete(`Xóa ${ids.length} bản ghi đã chọn?`, async () => {
      setConfirm(null)
      await historyApi.deleteBulk(ids)
      setSelectedIds(new Set())
      load({ page, limit: LIMIT, ...buildFilterParams() })
    })
  }

  // ── Rename ─────────────────────────────────────────────────────────────────

  const handleRename = async (id: number, title: string) => {
    const updated = await historyApi.updateTitle(id, title)
    setPageData((prev) => ({
      ...prev,
      items: prev.items.map((item) => (item.id === id ? { ...item, title: updated.title } : item)),
    }))
  }

  // ── ZIP Download ───────────────────────────────────────────────────────────

  const handleBulkDownload = async () => {
    const selected = pageData.items.filter((i) => selectedIds.has(i.id) && i.audio_url)
    if (selected.length === 0) return
    setBulkDownloading(true)
    try {
      const zip = new JSZip()
      await Promise.all(
        selected.map(async (item) => {
          const res = await fetch(item.audio_url!)
          const blob = await res.blob()
          zip.file(`${item.title || `job_${item.id}`}.${item.format}`, blob)
        })
      )
      const blob = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `voxify_history_${Date.now()}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setBulkDownloading(false)
    }
  }

  // ── Reopen in TTS ──────────────────────────────────────────────────────────

  const handleReopen = (item: HistoryItem) => {
    navigate('/tts', { state: { reopenJob: item } })
  }

  // ── Sao chép nội dung văn bản ──────────────────────────────────────────────

  const handleCopyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Đã sao chép nội dung vào khay nhớ tạm!')
    } catch {
      toast.error('Không thể sao chép văn bản.')
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  const buildFilterParams = (): Omit<HistoryListParams, 'page' | 'limit'> => ({
    ...(filter.search ? { search: filter.search } : {}),
    ...(filter.status ? { status: filter.status } : {}),
    ...(filter.format ? { format: filter.format } : {}),
    ...(filter.date_from ? { date_from: filter.date_from } : {}),
    ...(filter.date_to ? { date_to: filter.date_to } : {}),
  })

  const { items, total, pages } = pageData
  const start = (page - 1) * LIMIT + 1
  const end = Math.min(page * LIMIT, total)
  const hasFilters = Object.values(filter).some(Boolean)

  // ── Pagination range ───────────────────────────────────────────────────────

  const pageRange = (): (number | '...')[] => {
    if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
    const result: (number | '...')[] = [1]
    if (page > 3) result.push('...')
    for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) result.push(i)
    if (page < pages - 2) result.push('...')
    result.push(pages)
    return result
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-2 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <HistoryIcon className="w-7 h-7 text-indigo-500" />
            Lịch sử xử lý
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1">
            Quản lý toàn bộ các đoạn âm thanh đã tạo — nghe lại, tải về hoặc tái sử dụng ngay.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white dark:bg-white/5 rounded-card border border-slate-200 dark:border-white/10 p-4">
        <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={filter.search}
              onChange={(e) => updateFilter('search', e.target.value)}
              placeholder="Tìm kiếm nội dung, tên..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-white/30 focus:outline-none focus:border-indigo-400 dark:focus:border-indigo-500 transition-colors"
            />
          </div>

          {/* Status */}
          <select
            value={filter.status}
            onChange={(e) => updateFilter('status', e.target.value)}
            className="px-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-white/80 focus:outline-none focus:border-indigo-400 dark:focus:border-indigo-500 transition-colors"
          >
            <option value="">Tất cả trạng thái</option>
            <option value="done">Thành công</option>
            <option value="processing">Đang xử lý</option>
            <option value="queued">Chờ xử lý</option>
            <option value="failed">Thất bại</option>
          </select>

          {/* Format */}
          <select
            value={filter.format}
            onChange={(e) => updateFilter('format', e.target.value)}
            className="px-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-white/80 focus:outline-none focus:border-indigo-400 dark:focus:border-indigo-500 transition-colors"
          >
            <option value="">Tất cả định dạng</option>
            <option value="mp3">MP3</option>
            <option value="wav">WAV</option>
          </select>

          {/* Date from */}
          <input
            type="date"
            value={filter.date_from}
            onChange={(e) => updateFilter('date_from', e.target.value)}
            className="px-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-white/80 focus:outline-none focus:border-indigo-400 dark:focus:border-indigo-500 transition-colors"
            title="Từ ngày"
          />

          {/* Date to */}
          <input
            type="date"
            value={filter.date_to}
            onChange={(e) => updateFilter('date_to', e.target.value)}
            className="px-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-white/80 focus:outline-none focus:border-indigo-400 dark:focus:border-indigo-500 transition-colors"
            title="Đến ngày"
          />

          {/* Reset */}
          {hasFilters && (
            <button
              onClick={resetFilter}
              className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Đặt lại
            </button>
          )}
        </div>
      </div>

      {/* Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between gap-3 bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 rounded-card px-4 py-3">
          <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
            Đã chọn {selectedIds.size} mục
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkDownload}
              disabled={bulkDownloading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-control bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors disabled:opacity-60"
            >
              {bulkDownloading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Archive className="w-3.5 h-3.5" />
              )}
              Tải ZIP
            </button>
            <button
              onClick={handleDeleteBulk}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-control bg-rose-600 hover:bg-rose-700 text-white font-medium transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Xóa đã chọn
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-white/5 rounded-card border border-slate-200 dark:border-white/10 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50 dark:bg-white/5 border-b border-slate-200 dark:border-white/10">
                {/* Checkbox */}
                <th className="py-3 px-4 w-10">
                  <button
                    onClick={toggleSelectAll}
                    className="text-slate-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors"
                    aria-label="Chọn tất cả"
                  >
                    {isAllSelected ? (
                      <CheckSquare className="w-4 h-4" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Nội dung</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Giọng đọc</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Thời lượng</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Credit</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Định dạng</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Trạng thái</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap">Ngày tạo</th>
                <th className="py-3 px-4 text-xs uppercase font-semibold text-slate-500 dark:text-white/40 whitespace-nowrap text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
              ) : error ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <AlertCircle className="w-10 h-10 text-rose-400" />
                      <p className="text-sm text-slate-500 dark:text-white/50">{error}</p>
                      <button
                        onClick={() => load({ page, limit: LIMIT, ...buildFilterParams() })}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Thử lại
                      </button>
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-20 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <HistoryIcon className="w-14 h-14 text-slate-200 dark:text-white/10" />
                      <div>
                        <p className="text-sm font-medium text-slate-500 dark:text-white/40">
                          {hasFilters ? 'Không tìm thấy kết quả phù hợp' : 'Chưa có lịch sử xử lý nào'}
                        </p>
                        <p className="text-xs text-slate-400 dark:text-white/25 mt-1">
                          {hasFilters ? 'Hãy thử thay đổi bộ lọc' : 'Hãy tạo bài đọc đầu tiên tại Studio'}
                        </p>
                      </div>
                      {hasFilters && (
                        <button
                          onClick={resetFilter}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Đặt lại bộ lọc
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const isExpanded = expandedId === item.id
                  const isSelected = selectedIds.has(item.id)

                  return (
                    <>
                      <tr
                        key={item.id}
                        className={clsx(
                          'border-b border-slate-100 dark:border-white/[0.05] transition-colors',
                          isSelected
                            ? 'bg-indigo-50/60 dark:bg-indigo-500/[0.07]'
                            : 'hover:bg-slate-50/80 dark:hover:bg-white/[0.02]'
                        )}
                      >
                        {/* Checkbox */}
                        <td className="py-3 px-4 w-10">
                          <button
                            onClick={() => toggleSelect(item.id)}
                            className="text-slate-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors"
                            aria-label={`Chọn bản ghi ${item.id}`}
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-indigo-500" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        </td>

                        {/* Title / Content */}
                        <td className="py-3 px-4 max-w-[220px]">
                          <TitleEditor item={item} onSave={handleRename} />
                          <p className="text-xs text-slate-400 dark:text-white/30 mt-0.5 line-clamp-1">
                            {item.text.slice(0, 60)}{item.text.length > 60 ? '…' : ''}
                          </p>
                        </td>

                        {/* Voice */}
                        <td className="py-3 px-4 text-sm text-slate-600 dark:text-white/60 whitespace-nowrap">
                          <div className="flex items-center gap-1">
                            <Volume2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate max-w-[120px]" title={item.voice}>
                              {item.voice}
                            </span>
                          </div>
                        </td>

                        {/* Duration */}
                        <td className="py-3 px-4 font-mono text-sm text-slate-700 dark:text-white/70 whitespace-nowrap">
                          {formatDuration(item.duration)}
                        </td>

                        {/* Credit */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="inline-flex items-center gap-1 font-mono text-sm text-amber-600 dark:text-amber-400 font-semibold">
                            <Coins className="w-3.5 h-3.5" />
                            {item.credit_used.toLocaleString('vi-VN')}
                          </span>
                        </td>

                        {/* Format */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <FormatBadge format={item.format} />
                        </td>

                        {/* Status */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <StatusBadge status={item.status} progress={item.progress} />
                          {item.status === 'failed' && item.error_message && (
                            <p className="text-[10px] text-rose-500 mt-0.5 max-w-[160px] truncate" title={item.error_message}>
                              {item.error_message}
                            </p>
                          )}
                        </td>

                        {/* Date */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          {item.created_at ? (
                            <div>
                              <p className="text-xs font-mono text-slate-500 dark:text-white/40">
                                {formatDate(item.created_at)}
                              </p>
                              <p className="text-[10px] text-slate-400 dark:text-white/25 mt-0.5">
                                {formatRelativeTime(item.created_at)}
                              </p>
                            </div>
                          ) : (
                            <span className="text-slate-300 dark:text-white/20">&mdash;</span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1">
                            {/* Play */}
                            {item.audio_url && (
                              <button
                                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                                className={clsx(
                                  'p-1.5 rounded-control transition-colors',
                                  isExpanded
                                    ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400'
                                    : 'text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-indigo-600 dark:hover:text-indigo-400'
                                )}
                                title="Nghe thử"
                              >
                                <Play className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {/* Download audio */}
                            {item.audio_url && (
                              <a
                                href={item.audio_url}
                                download
                                className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                                title="Tải xuống"
                              >
                                <Download className="w-3.5 h-3.5" />
                              </a>
                            )}

                            {/* SRT */}
                            {item.srt_url && (
                              <a
                                href={item.srt_url}
                                download
                                className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                                title="Tải SRT"
                              >
                                <Subtitles className="w-3.5 h-3.5" />
                              </a>
                            )}

                            {/* VTT */}
                            {item.vtt_url && (
                              <a
                                href={item.vtt_url}
                                download
                                className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                title="Tải VTT"
                              >
                                <FileText className="w-3.5 h-3.5" />
                              </a>
                            )}

                            {/* Reopen */}
                            <button
                              onClick={() => handleReopen(item)}
                              className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                              title="Mở lại trong Studio"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>

                            {/* Copy text */}
                            <button
                              onClick={() => handleCopyText(item.text)}
                              className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                              title="Sao chép nội dung"
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </button>

                            {/* Delete */}
                            <button
                              onClick={() => handleDeleteOne(item.id)}
                              className="p-1.5 rounded-control text-slate-500 dark:text-white/50 hover:bg-rose-50 dark:hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
                              title="Xóa"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Audio Player */}
                      {isExpanded && item.audio_url && (
                        <tr
                          key={`${item.id}-player`}
                          className="bg-indigo-50/40 dark:bg-indigo-500/[0.05] border-b border-slate-100 dark:border-white/[0.05]"
                        >
                          <td colSpan={9} className="px-4">
                            <AudioPlayerRow audioUrl={item.audio_url} />
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {!loading && !error && total > 0 && (
          <div className="p-3 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-white/[0.02] flex items-center justify-between gap-3 flex-wrap text-xs">
            <span className="text-slate-500 dark:text-white/40 font-mono">
              Hiển thị {start}–{end} trong {total} kết quả
            </span>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Trang trước"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {pageRange().map((p, i) =>
                p === '...' ? (
                  <span key={`ellipsis-${i}`} className="px-2 text-slate-400 dark:text-white/30">
                    …
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={clsx(
                      'w-7 h-7 rounded-control text-xs font-medium transition-colors',
                      p === page
                        ? 'bg-indigo-600 text-white'
                        : 'border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5'
                    )}
                  >
                    {p}
                  </button>
                )
              )}

              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page >= pages}
                className="p-1.5 rounded-control border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/70 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Trang sau"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Confirm Dialog */}
      {confirm && (
        <ConfirmDialog
          message={confirm.message}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}
