import { useState, useMemo, useEffect, useRef } from 'react'
import {
  Search,
  Star,
  Play,
  Pause,
  Check,
  X,
  Sparkles,
  Mic,
  Trash2,
  Plus,
  Loader2,
  Layers,
} from 'lucide-react'
import type { Voice } from '../../api/tts'
import {
  deleteClonedVoice,
  getVoiceCloneLimits,
  type ClonedVoice,
  type VoiceCloneQuota,
} from '../../api/voice_clone'
import {
  fetchVoiceLibrary,
  toggleVoiceFavorite,
  type VoiceLibraryItem,
} from '../../api/voice_library'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import VoiceCloneModal from '../studio/VoiceCloneModal'

interface VoicePickerProps {
  isOpen: boolean
  onClose: () => void
  voices?: Voice[]
  selectedVoiceId: string
  onSelectVoice: (voiceId: string) => void
  onPreviewSample?: (voiceId: string) => void
  defaultTab?: 'system' | 'cloned'
}

type GroupFilter = 'all' | 'mine' | 'favorites' | 'vi' | 'other'

export default function VoicePicker({
  isOpen,
  onClose,
  voices: propVoices = [],
  selectedVoiceId,
  onSelectVoice,
  onPreviewSample,
}: VoicePickerProps) {
  const { user } = useAuth()
  const toast = useToast()

  const [groupFilter, setGroupFilter] = useState<GroupFilter>('all')
  const [search, setSearch] = useState('')
  const [genderFilter, setGenderFilter] = useState<'all' | 'Female' | 'Male'>('all')

  // Unified voice library state
  const [libraryVoices, setLibraryVoices] = useState<VoiceLibraryItem[]>([])
  const [isLoadingLibrary, setIsLoadingLibrary] = useState(false)

  // Cloned quota & modal state
  const [_clonedQuota, setClonedQuota] = useState<VoiceCloneQuota | null>(null)
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false)
  const [deletingVoiceRef, setDeletingVoiceRef] = useState<string | null>(null)

  // Audio preview playback
  const [playingVoiceId, setPlayingVoiceId] = useState<number | string | null>(null)
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null)

  const loadUnifiedVoices = async () => {
    setIsLoadingLibrary(true)
    try {
      const res = await fetchVoiceLibrary({ limit: 500 })
      setLibraryVoices(res.voices || [])
    } catch {
      // Fallback: If library endpoint fails or offline, construct items from propVoices
      if (propVoices.length > 0) {
        const fallbacks: VoiceLibraryItem[] = propVoices.map((pv, idx) => ({
          id: idx + 1,
          owner_id: null,
          name: pv.name,
          display_name: pv.full_name || pv.name,
          description: null,
          provider: 'edge',
          provider_voice_id: pv.id,
          voice_type: 'system',
          language: pv.locale,
          gender: pv.gender,
          tags: null,
          preview_url: null,
          sample_duration: null,
          visibility: 'public',
          status: 'ready',
          is_active: true,
          tier: 'free',
          credit_multiplier: 1.0,
          cloned_voice_ref: null,
          total_uses: 0,
          created_at: new Date().toISOString(),
          is_favorite: false,
        }))
        setLibraryVoices(fallbacks)
      }
    } finally {
      setIsLoadingLibrary(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadUnifiedVoices()
      if (user) {
        getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
      }
    } else {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
        setPlayingVoiceId(null)
      }
    }
  }, [isOpen])

  const handleToggleFavorite = async (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await toggleVoiceFavorite(voice.id)
      setLibraryVoices((prev) =>
        prev.map((v) => (v.id === voice.id ? { ...v, is_favorite: res.is_favorite } : v))
      )
      toast.info(res.is_favorite ? 'Đã thêm vào yêu thích' : 'Đã bỏ yêu thích')
    } catch {
      toast.error('Không thể cập nhật danh sách yêu thích.')
    }
  }

  const handlePlayPreview = (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    const targetId = voice.id
    if (playingVoiceId === targetId) {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
      }
      setPlayingVoiceId(null)
      return
    }

    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause()
    }

    let previewSrc = voice.preview_url
    if (!previewSrc && voice.voice_type === 'cloned' && voice.cloned_voice_ref) {
      previewSrc = `/api/voices/cloned/${voice.cloned_voice_ref}/preview`
    } else if (!previewSrc && voice.provider_voice_id) {
      previewSrc = `/api/tts/sample?voice=${encodeURIComponent(voice.provider_voice_id)}`
    }

    if (!previewSrc) {
      if (onPreviewSample && voice.provider_voice_id) {
        onPreviewSample(voice.provider_voice_id)
      } else {
        toast.info('Không có bản nghe thử cho giọng này.')
      }
      return
    }

    const audio = new Audio(previewSrc)
    audioPreviewRef.current = audio
    setPlayingVoiceId(targetId)

    audio.onended = () => {
      setPlayingVoiceId(null)
      audioPreviewRef.current = null
    }

    audio.onerror = () => {
      toast.error('Không thể phát bản nghe thử của giọng này.')
      setPlayingVoiceId(null)
      audioPreviewRef.current = null
    }

    audio.play().catch(() => {
      setPlayingVoiceId(null)
      audioPreviewRef.current = null
    })
  }

  const handleDeleteClonedVoice = async (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    const targetRef = voice.cloned_voice_ref || voice.provider_voice_id
    if (!targetRef) return

    const confirm = window.confirm(
      `Bạn có chắc chắn muốn xóa vĩnh viễn giọng clone "${voice.name}"? Tệp mẫu âm thanh và bản nghe thử sẽ bị xóa khỏi hệ thống.`
    )
    if (!confirm) return

    setDeletingVoiceRef(targetRef)
    try {
      await deleteClonedVoice(targetRef)
      toast.success(`Đã xóa thành công giọng clone "${voice.name}"`)
      setLibraryVoices((prev) =>
        prev.filter((v) => v.cloned_voice_ref !== targetRef && v.provider_voice_id !== targetRef)
      )
      if (selectedVoiceId === targetRef && libraryVoices.length > 0) {
        const next = libraryVoices.find((v) => v.provider_voice_id !== targetRef)
        if (next && next.provider_voice_id) {
          onSelectVoice(next.provider_voice_id)
        }
      }
      getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
    } catch {
      toast.error('Xóa giọng clone thất bại, vui lòng thử lại sau.')
    } finally {
      setDeletingVoiceRef(null)
    }
  }

  const handleVoiceCloneCreated = (newCloned: ClonedVoice) => {
    onSelectVoice(newCloned.voice_id)
    toast.success(`Đã tạo và kích hoạt giọng clone "${newCloned.name}"!`)
    setIsCloneModalOpen(false)
    loadUnifiedVoices()
    getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
  }

  // Filtered voices according to search & gender
  const filteredVoices = useMemo(() => {
    return libraryVoices.filter((v) => {
      if (genderFilter !== 'all' && v.gender.toLowerCase() !== genderFilter.toLowerCase()) {
        return false
      }
      if (search.trim()) {
        const q = search.toLowerCase()
        const matchName = v.name.toLowerCase().includes(q)
        const matchDisplay = v.display_name?.toLowerCase().includes(q)
        const matchLang = v.language.toLowerCase().includes(q)
        return matchName || matchDisplay || matchLang
      }
      return true
    })
  }, [libraryVoices, genderFilter, search])

  // Grouped voices: Giọng của tôi / Yêu thích / Tiếng Việt / Khác
  const groups = useMemo(() => {
    const mine: VoiceLibraryItem[] = []
    const favorites: VoiceLibraryItem[] = []
    const vietnamese: VoiceLibraryItem[] = []
    const other: VoiceLibraryItem[] = []

    for (const v of filteredVoices) {
      if (v.voice_type === 'cloned') {
        mine.push(v)
      } else if (v.is_favorite) {
        favorites.push(v)
      } else if (v.language.toLowerCase().startsWith('vi')) {
        vietnamese.push(v)
      } else {
        other.push(v)
      }
    }

    return { mine, favorites, vietnamese, other }
  }, [filteredVoices])

  if (!isOpen) return null

  const renderVoiceCard = (voice: VoiceLibraryItem) => {
    const voiceRef = voice.provider_voice_id || voice.name
    const isSelected =
      selectedVoiceId === voiceRef ||
      (voice.cloned_voice_ref && selectedVoiceId === voice.cloned_voice_ref)
    const isPlaying = playingVoiceId === voice.id
    const isCloned = voice.voice_type === 'cloned'
    const isDeleting =
      deletingVoiceRef === (voice.cloned_voice_ref || voice.provider_voice_id)

    return (
      <div
        key={voice.id}
        onClick={() => {
          onSelectVoice(voiceRef)
          onClose()
        }}
        className={`p-3 rounded-card border transition-all cursor-pointer flex items-center justify-between group ${
          isSelected
            ? 'bg-indigo-50 border-indigo-500/60 text-indigo-950 dark:bg-indigo-600/20 dark:border-indigo-500/60 dark:text-white shadow-xs'
            : isCloned
            ? 'bg-white hover:bg-purple-50/50 border-purple-200/80 dark:bg-[#181C25]/50 dark:hover:bg-[#1e1b2e] dark:border-purple-500/20 hover:border-purple-500/40'
            : 'bg-white hover:bg-slate-50 border-slate-200/80 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] dark:border-white/[0.06] hover:border-indigo-500/30'
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-10 h-10 rounded-control flex items-center justify-center font-bold text-xs flex-shrink-0 ${
              isCloned
                ? 'bg-gradient-to-br from-purple-500/20 to-indigo-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30'
                : voice.gender.toLowerCase() === 'female'
                ? 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20'
                : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
            }`}
          >
            {isCloned ? '✨' : voice.gender.toLowerCase() === 'female' ? '♀' : '♂'}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                {voice.display_name || voice.name}
              </span>
              {isCloned && (
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                  Clone
                </span>
              )}
              {voice.language.toLowerCase().startsWith('vi') && !isCloned && (
                <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-500/30">
                  Tiếng Việt
                </span>
              )}
              {voice.credit_multiplier > 1.0 && (
                <span className="text-[9px] font-bold px-1 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  {voice.credit_multiplier}x
                </span>
              )}
              <span className="text-[10px] text-slate-500 dark:text-white/40">
                {voice.gender.toLowerCase() === 'female' ? 'Nữ' : 'Nam'}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-white/40 truncate mt-0.5">
              {voice.description || voice.language}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Preview Play/Pause button */}
          <button
            onClick={(e) => handlePlayPreview(voice, e)}
            className={`p-1.5 rounded-control transition-colors ${
              isPlaying
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-400 hover:text-slate-800 hover:bg-slate-100 dark:hover:text-white dark:hover:bg-white/10'
            }`}
            title={isPlaying ? 'Dừng phát' : 'Nghe thử bản preview'}
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
          </button>

          {/* Favorite Star Button */}
          <button
            onClick={(e) => handleToggleFavorite(voice, e)}
            className={`p-1.5 rounded-control transition-colors ${
              voice.is_favorite
                ? 'text-amber-500'
                : 'text-slate-300 dark:text-white/30 hover:text-amber-500 hover:bg-slate-100 dark:hover:bg-white/5'
            }`}
            title={voice.is_favorite ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
          >
            <Star className={`w-3.5 h-3.5 ${voice.is_favorite ? 'fill-current' : ''}`} />
          </button>

          {/* Delete button if cloned */}
          {isCloned && (
            <button
              disabled={isDeleting}
              onClick={(e) => handleDeleteClonedVoice(voice, e)}
              className="p-1.5 rounded-control text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors disabled:opacity-40"
              title="Xóa giọng clone này"
            >
              {isDeleting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-500" />
              ) : (
                <Trash2 className="w-3.5 h-3.5" />
              )}
            </button>
          )}

          {isSelected && (
            <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs ml-1">
              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />

        {/* Modal Dialog */}
        <div className="relative w-full max-w-2xl max-h-[85vh] rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.1] shadow-2xl flex flex-col z-10 animate-in fade-in zoom-in-95 duration-150 overflow-hidden">
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Thư viện Giọng đọc AI
                </h2>
                <p className="text-xs text-slate-500 dark:text-white/40">
                  Chọn giọng đọc hệ thống tự nhiên hoặc clone giọng cá nhân của bạn
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-control text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Group Tabs Selector: Tất cả | Giọng của tôi | Yêu thích | Tiếng Việt | Khác */}
          <div className="flex items-center px-4 pt-3 border-b border-slate-200 dark:border-white/[0.06] bg-slate-50/50 dark:bg-[#0B0D12]/30 gap-1.5 overflow-x-auto">
            <button
              onClick={() => setGroupFilter('all')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                groupFilter === 'all'
                  ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Tất cả ({libraryVoices.length})</span>
            </button>

            <button
              onClick={() => setGroupFilter('mine')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                groupFilter === 'mine'
                  ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-600 dark:border-purple-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <Mic className="w-3.5 h-3.5 text-purple-500" />
              <span>Giọng của tôi ({groups.mine.length})</span>
            </button>

            <button
              onClick={() => setGroupFilter('favorites')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                groupFilter === 'favorites'
                  ? 'text-amber-500 border-b-2 border-amber-500'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <Star className="w-3.5 h-3.5 fill-current text-amber-400" />
              <span>Yêu thích ({groups.favorites.length})</span>
            </button>

            <button
              onClick={() => setGroupFilter('vi')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                groupFilter === 'vi'
                  ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <span>Tiếng Việt ({groups.vietnamese.length})</span>
            </button>

            <button
              onClick={() => setGroupFilter('other')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                groupFilter === 'other'
                  ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <span>Khác ({groups.other.length})</span>
            </button>
          </div>

          {/* Search & Sub-filter Header */}
          <div className="p-3 border-b border-slate-200/80 dark:border-white/[0.06] flex items-center justify-between gap-3 bg-white dark:bg-[#12151C]">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 dark:text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm giọng theo tên..."
                className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-control pl-9 pr-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2">
              {/* Gender Filter */}
              <div className="flex bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08] text-xs">
                <button
                  onClick={() => setGenderFilter('all')}
                  className={`px-2 py-1 rounded-[6px] font-medium transition-all ${
                    genderFilter === 'all'
                      ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Tất cả
                </button>
                <button
                  onClick={() => setGenderFilter('Female')}
                  className={`px-2 py-1 rounded-[6px] font-medium transition-all ${
                    genderFilter === 'Female'
                      ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Nữ
                </button>
                <button
                  onClick={() => setGenderFilter('Male')}
                  className={`px-2 py-1 rounded-[6px] font-medium transition-all ${
                    genderFilter === 'Male'
                      ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Nam
                </button>
              </div>

              {/* Create Clone Voice Shortcut */}
              <button
                onClick={() => setIsCloneModalOpen(true)}
                className="px-2.5 py-1.5 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold flex items-center gap-1 shadow-xs transition-transform active:scale-95"
              >
                <Plus className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Clone mới</span>
              </button>
            </div>
          </div>

          {/* Voices List / Group Sections */}
          <div className="p-4 overflow-y-auto space-y-4 flex-1">
            {isLoadingLibrary ? (
              <div className="py-16 flex flex-col items-center justify-center gap-2 text-xs text-slate-400 dark:text-white/40">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
                <span>Đang tải danh sách giọng đọc...</span>
              </div>
            ) : filteredVoices.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 dark:text-white/40">
                Không tìm thấy giọng đọc nào phù hợp.
              </div>
            ) : (
              <>
                {/* 1. Group: Giọng của tôi */}
                {(groupFilter === 'all' || groupFilter === 'mine') && groups.mine.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-purple-600 dark:text-purple-400">
                      <Mic className="w-3.5 h-3.5" />
                      <span>Giọng của tôi ({groups.mine.length})</span>
                    </div>
                    <div className="space-y-2">
                      {groups.mine.map(renderVoiceCard)}
                    </div>
                  </div>
                )}

                {/* 2. Group: Yêu thích */}
                {(groupFilter === 'all' || groupFilter === 'favorites') &&
                  groups.favorites.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-bold text-amber-500">
                        <Star className="w-3.5 h-3.5 fill-current" />
                        <span>Yêu thích ({groups.favorites.length})</span>
                      </div>
                      <div className="space-y-2">
                        {groups.favorites.map(renderVoiceCard)}
                      </div>
                    </div>
                  )}

                {/* 3. Group: Tiếng Việt */}
                {(groupFilter === 'all' || groupFilter === 'vi') &&
                  groups.vietnamese.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
                        <Layers className="w-3.5 h-3.5" />
                        <span>Tiếng Việt ({groups.vietnamese.length})</span>
                      </div>
                      <div className="space-y-2">
                        {groups.vietnamese.map(renderVoiceCard)}
                      </div>
                    </div>
                  )}

                {/* 4. Group: Khác */}
                {(groupFilter === 'all' || groupFilter === 'other') && groups.other.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-white/50">
                      <Layers className="w-3.5 h-3.5" />
                      <span>Khác ({groups.other.length})</span>
                    </div>
                    <div className="space-y-2">
                      {groups.other.map(renderVoiceCard)}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Voice Clone Modal */}
      <VoiceCloneModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        onVoiceCreated={handleVoiceCloneCreated}
      />
    </>
  )
}
