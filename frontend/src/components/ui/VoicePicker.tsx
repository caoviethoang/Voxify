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
  listClonedVoices,
  deleteClonedVoice,
  getVoiceCloneLimits,
  type ClonedVoice,
  type VoiceCloneQuota,
} from '../../api/voice_clone'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import VoiceCloneModal from '../studio/VoiceCloneModal'

interface VoicePickerProps {
  isOpen: boolean
  onClose: () => void
  voices: Voice[]
  selectedVoiceId: string
  onSelectVoice: (voiceId: string) => void
  onPreviewSample?: (voiceId: string) => void
  defaultTab?: 'system' | 'cloned'
}

export default function VoicePicker({
  isOpen,
  onClose,
  voices,
  selectedVoiceId,
  onSelectVoice,
  onPreviewSample,
  defaultTab = 'system',
}: VoicePickerProps) {
  const { user } = useAuth()
  const toast = useToast()

  const [activeTab, setActiveTab] = useState<'system' | 'cloned'>(defaultTab)
  const [search, setSearch] = useState('')
  const [genderFilter, setGenderFilter] = useState<'all' | 'Female' | 'Male'>('all')
  const [langFilter, setLangFilter] = useState<'vi' | 'all'>('vi')
  const [favorites, setFavorites] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('voxify_favorite_voices') || '[]')
    } catch {
      return []
    }
  })

  // Cloned voices state
  const [clonedVoices, setClonedVoices] = useState<ClonedVoice[]>([])
  const [isLoadingCloned, setIsLoadingCloned] = useState(false)
  const [clonedQuota, setClonedQuota] = useState<VoiceCloneQuota | null>(null)
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false)
  const [deletingVoiceId, setDeletingVoiceId] = useState<string | null>(null)

  // Audio preview playback for cloned voices
  const [playingClonedId, setPlayingClonedId] = useState<string | null>(null)
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null)

  // Load cloned voices when modal is opened
  const fetchClonedData = async () => {
    if (!user) return
    setIsLoadingCloned(true)
    try {
      const [listRes, quotaRes] = await Promise.all([
        listClonedVoices(),
        getVoiceCloneLimits().catch(() => null),
      ])
      setClonedVoices(listRes.voices || [])
      if (quotaRes) setClonedQuota(quotaRes)
    } catch {
      // Offline or network error
    } finally {
      setIsLoadingCloned(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      // If currently selected voice is a clone voice, switch to cloned tab
      if (selectedVoiceId.startsWith('clone_')) {
        setActiveTab('cloned')
      } else {
        setActiveTab(defaultTab)
      }
      fetchClonedData()
    } else {
      // Stop preview audio when closed
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
        setPlayingClonedId(null)
      }
    }
  }, [isOpen, selectedVoiceId, defaultTab])

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const next = favorites.includes(id)
      ? favorites.filter((fav) => fav !== id)
      : [...favorites, id]
    setFavorites(next)
    localStorage.setItem('voxify_favorite_voices', JSON.stringify(next))
  }

  const handlePlayClonedPreview = (voice: ClonedVoice, e: React.MouseEvent) => {
    e.stopPropagation()
    if (playingClonedId === voice.voice_id) {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
      }
      setPlayingClonedId(null)
      return
    }

    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause()
    }

    const previewSrc =
      voice.preview_audio_url || voice.preview_url || `/api/voices/cloned/${voice.voice_id}/preview`
    const audio = new Audio(previewSrc)
    audioPreviewRef.current = audio
    setPlayingClonedId(voice.voice_id)

    audio.onended = () => {
      setPlayingClonedId(null)
      audioPreviewRef.current = null
    }

    audio.onerror = () => {
      toast.error('Không thể phát bản nghe thử của giọng clone này.')
      setPlayingClonedId(null)
      audioPreviewRef.current = null
    }

    audio.play().catch(() => {
      setPlayingClonedId(null)
      audioPreviewRef.current = null
    })
  }

  const handleDeleteClonedVoice = async (voice: ClonedVoice, e: React.MouseEvent) => {
    e.stopPropagation()
    const confirm = window.confirm(
      `Bạn có chắc chắn muốn xóa vĩnh viễn giọng clone "${voice.name}"? Tệp mẫu âm thanh và bản nghe thử sẽ bị xóa khỏi hệ thống.`
    )
    if (!confirm) return

    setDeletingVoiceId(voice.voice_id)
    try {
      await deleteClonedVoice(voice.voice_id)
      toast.success(`Đã xóa thành công giọng clone "${voice.name}"`)
      setClonedVoices((prev) => prev.filter((v) => v.voice_id !== voice.voice_id))
      if (selectedVoiceId === voice.voice_id && voices.length > 0) {
        onSelectVoice(voices[0].id)
      }
      // Refresh quota
      getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
    } catch {
      toast.error('Xóa giọng clone thất bại, vui lòng thử lại sau.')
    } finally {
      setDeletingVoiceId(null)
    }
  }

  const handleVoiceCloneCreated = (newVoice: ClonedVoice) => {
    setClonedVoices((prev) => [newVoice, ...prev])
    onSelectVoice(newVoice.voice_id)
    toast.success(`Đã tạo và kích hoạt giọng clone "${newVoice.name}"!`)
    setIsCloneModalOpen(false)
    setActiveTab('cloned')
    getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
  }

  const filteredVoices = useMemo(() => {
    return voices.filter((v) => {
      if (langFilter === 'vi' && !v.locale.toLowerCase().startsWith('vi')) {
        return false
      }
      if (genderFilter !== 'all' && v.gender.toLowerCase() !== genderFilter.toLowerCase()) {
        return false
      }
      if (search.trim()) {
        const q = search.toLowerCase()
        const matchName = v.name.toLowerCase().includes(q)
        const matchFullName = v.full_name?.toLowerCase().includes(q)
        const matchLocale = v.locale_name?.toLowerCase().includes(q)
        return matchName || matchFullName || matchLocale
      }
      return true
    })
  }, [voices, langFilter, genderFilter, search])

  const filteredClonedVoices = useMemo(() => {
    if (!search.trim()) return clonedVoices
    const q = search.toLowerCase()
    return clonedVoices.filter(
      (v) => v.name.toLowerCase().includes(q) || (v.description && v.description.toLowerCase().includes(q))
    )
  }, [clonedVoices, search])

  if (!isOpen) return null

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

          {/* Tab Selector */}
          <div className="flex items-center px-4 pt-3 border-b border-slate-200 dark:border-white/[0.06] bg-slate-50/50 dark:bg-[#0B0D12]/30 gap-2">
            <button
              onClick={() => setActiveTab('system')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all relative flex items-center gap-1.5 ${
                activeTab === 'system'
                  ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Thư viện hệ thống ({voices.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('cloned')}
              className={`pb-2.5 px-3 font-semibold text-xs transition-all relative flex items-center gap-1.5 ${
                activeTab === 'cloned'
                  ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-600 dark:border-purple-400'
                  : 'text-slate-500 dark:text-white/50 hover:text-slate-800 dark:hover:text-white'
              }`}
            >
              <Mic className="w-3.5 h-3.5 text-purple-500" />
              <span>Giọng của tôi ({clonedVoices.length})</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                Clone
              </span>
            </button>
          </div>

          {/* TAB 1: THƯ VIỆN HỆ THỐNG */}
          {activeTab === 'system' && (
            <>
              {/* Filter & Search Bar */}
              <div className="p-4 border-b border-slate-200 dark:border-white/[0.06] bg-slate-50/70 dark:bg-[#0B0D12]/40 space-y-3">
                {/* Search box */}
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 dark:text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Tìm theo tên giọng (Hoài My, Nam Minh...), ngôn ngữ, vùng miền..."
                    className="w-full bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-control pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Filter Pills */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {/* Lang filters */}
                  <div className="flex bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08]">
                    <button
                      onClick={() => setLangFilter('vi')}
                      className={`px-3 py-1 rounded-[8px] font-semibold transition-all ${
                        langFilter === 'vi'
                          ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                          : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      Tiếng Việt ({voices.filter((v) => v.locale.toLowerCase().startsWith('vi')).length})
                    </button>
                    <button
                      onClick={() => setLangFilter('all')}
                      className={`px-3 py-1 rounded-[8px] font-semibold transition-all ${
                        langFilter === 'all'
                          ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                          : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      Tất cả ({voices.length})
                    </button>
                  </div>

                  {/* Gender filters */}
                  <div className="flex bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08]">
                    <button
                      onClick={() => setGenderFilter('all')}
                      className={`px-2.5 py-1 rounded-[8px] font-medium transition-all ${
                        genderFilter === 'all'
                          ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                          : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      Tất cả giới tính
                    </button>
                    <button
                      onClick={() => setGenderFilter('Female')}
                      className={`px-2.5 py-1 rounded-[8px] font-medium transition-all ${
                        genderFilter === 'Female'
                          ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                          : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      Nữ
                    </button>
                    <button
                      onClick={() => setGenderFilter('Male')}
                      className={`px-2.5 py-1 rounded-[8px] font-medium transition-all ${
                        genderFilter === 'Male'
                          ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                          : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      Nam
                    </button>
                  </div>
                </div>
              </div>

              {/* Voices Grid / List */}
              <div className="flex-1 overflow-y-auto p-4 max-h-[50vh] scrollbar-thin space-y-2">
                {filteredVoices.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-400 dark:text-white/40">
                    Không tìm thấy giọng đọc nào phù hợp với bộ lọc hiện tại.
                  </div>
                ) : (
                  filteredVoices.map((voice) => {
                    const isSelected = voice.id === selectedVoiceId
                    const isFav = favorites.includes(voice.id)

                    return (
                      <div
                        key={voice.id}
                        onClick={() => {
                          onSelectVoice(voice.id)
                          onClose()
                        }}
                        className={`p-3 rounded-card border transition-all cursor-pointer flex items-center justify-between group ${
                          isSelected
                            ? 'bg-indigo-50 border-indigo-500/60 text-indigo-950 dark:bg-indigo-600/20 dark:border-indigo-500/60 dark:text-white shadow-xs'
                            : 'bg-white hover:bg-slate-50 border-slate-200/80 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] dark:border-white/[0.06] hover:border-indigo-500/30'
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={`w-10 h-10 rounded-control flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                              voice.gender.toLowerCase() === 'female'
                                ? 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20'
                                : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
                            }`}
                          >
                            {voice.gender.toLowerCase() === 'female' ? '♀' : '♂'}
                          </div>

                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                                {voice.name}
                              </span>
                              {voice.locale.toLowerCase().startsWith('vi') && (
                                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-500/30">
                                  Tiếng Việt
                                </span>
                              )}
                              <span className="text-[10px] text-slate-500 dark:text-white/40">
                                {voice.gender.toLowerCase() === 'female' ? 'Nữ' : 'Nam'}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-white/40 truncate mt-0.5">
                              {voice.full_name || voice.id}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {onPreviewSample && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                onPreviewSample(voice.id)
                              }}
                              className="p-2 rounded-control text-slate-400 hover:text-slate-800 hover:bg-slate-100 dark:hover:text-white dark:hover:bg-white/10 transition-colors"
                              title="Nghe thử mẫu giọng"
                            >
                              <Play className="w-3.5 h-3.5 fill-current" />
                            </button>
                          )}

                          <button
                            onClick={(e) => toggleFavorite(voice.id, e)}
                            className={`p-2 rounded-control transition-colors ${
                              isFav
                                ? 'text-[#F59E0B]'
                                : 'text-slate-300 dark:text-white/30 hover:text-[#F59E0B] hover:bg-slate-100 dark:hover:bg-white/5'
                            }`}
                            title={isFav ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
                          >
                            <Star className={`w-3.5 h-3.5 ${isFav ? 'fill-current' : ''}`} />
                          </button>

                          {isSelected && (
                            <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs ml-1">
                              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </>
          )}

          {/* TAB 2: GIỌNG CỦA TÔI (VOICE CLONE) */}
          {activeTab === 'cloned' && (
            <div className="flex-1 overflow-y-auto p-4 max-h-[60vh] scrollbar-thin space-y-3">
              {/* Top Banner with Quota and Create button */}
              <div className="p-3.5 rounded-card bg-gradient-to-r from-purple-500/10 via-indigo-500/10 to-transparent border border-purple-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      Nhân bản giọng nói AI (Voice Cloning)
                    </span>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-700 dark:text-purple-300 border border-purple-500/30">
                      x1.5 Credit / lượt đọc
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-white/50 mt-1">
                    {clonedQuota ? (
                      <>
                        Gói {clonedQuota.plan_name}: Đã dùng {clonedQuota.used} / {clonedQuota.max_allowed} giọng clone cá nhân.
                      </>
                    ) : (
                      'Tải lên hoặc ghi âm 5–30 giây giọng thật để clone giọng đọc AI độc quyền của bạn.'
                    )}
                  </p>
                </div>

                <button
                  onClick={() => setIsCloneModalOpen(true)}
                  className="px-3.5 py-2 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/25 flex items-center gap-1.5 flex-shrink-0 transition-transform active:scale-95"
                >
                  <Plus className="w-3.5 h-3.5 stroke-[3]" />
                  <span>Tạo giọng clone mới</span>
                </button>
              </div>

              {/* Cloned Voices List */}
              {isLoadingCloned ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-xs text-slate-400 dark:text-white/40">
                  <Loader2 className="w-5 h-5 animate-spin text-purple-500" />
                  <span>Đang tải danh sách giọng clone của bạn...</span>
                </div>
              ) : filteredClonedVoices.length === 0 ? (
                <div className="py-12 px-4 text-center rounded-card border border-dashed border-slate-300 dark:border-white/10 flex flex-col items-center justify-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                    <Mic className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 dark:text-white">
                      Bạn chưa có giọng clone nào
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-white/40 mt-1 max-w-sm">
                      Bấm vào nút bên dưới để ghi âm hoặc tải lên mẫu âm thanh 5–30s tạo giọng AI của riêng bạn.
                    </p>
                  </div>
                  <button
                    onClick={() => setIsCloneModalOpen(true)}
                    className="px-4 py-2 rounded-control bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md shadow-purple-600/20 flex items-center gap-1.5 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Tạo giọng clone ngay</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredClonedVoices.map((voice) => {
                    const isSelected = voice.voice_id === selectedVoiceId
                    const isPlaying = playingClonedId === voice.voice_id
                    const isDeleting = deletingVoiceId === voice.voice_id

                    return (
                      <div
                        key={voice.voice_id}
                        onClick={() => {
                          onSelectVoice(voice.voice_id)
                          onClose()
                        }}
                        className={`p-3.5 rounded-card border transition-all cursor-pointer flex items-center justify-between group ${
                          isSelected
                            ? 'bg-purple-50 border-purple-500/60 text-purple-950 dark:bg-purple-600/20 dark:border-purple-500/60 dark:text-white shadow-xs'
                            : 'bg-white hover:bg-slate-50 border-slate-200/80 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] dark:border-white/[0.06] hover:border-purple-500/30'
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          {/* Avatar */}
                          <div className="w-10 h-10 rounded-control bg-gradient-to-br from-purple-500/20 to-indigo-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30 flex items-center justify-center font-bold text-xs flex-shrink-0">
                            ✨
                          </div>

                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                                {voice.name}
                              </span>
                              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                                Clone
                              </span>
                              <span className="text-[10px] text-slate-400 dark:text-white/40">
                                {voice.sample_duration ? `${voice.sample_duration.toFixed(1)}s` : ''}
                              </span>
                              {voice.quality_score && (
                                <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                                  ★ {voice.quality_score.toFixed(1)}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-white/40 truncate mt-0.5">
                              {voice.description || 'Giọng AI cá nhân tự tạo'}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {/* Nút nghe thử bản preview */}
                          <button
                            onClick={(e) => handlePlayClonedPreview(voice, e)}
                            className={`p-2 rounded-control transition-colors ${
                              isPlaying
                                ? 'bg-purple-600 text-white shadow-xs'
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

                          {/* Nút xóa giọng clone */}
                          <button
                            disabled={isDeleting}
                            onClick={(e) => handleDeleteClonedVoice(voice, e)}
                            className="p-2 rounded-control text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors disabled:opacity-40"
                            title="Xóa giọng clone này"
                          >
                            {isDeleting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-500" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {/* Checkmark nếu đang chọn */}
                          {isSelected && (
                            <div className="w-6 h-6 rounded-full bg-purple-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs ml-1">
                              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="p-3 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#0B0D12] flex items-center justify-between text-xs text-slate-500 dark:text-white/40">
            <span>
              {activeTab === 'system'
                ? `${filteredVoices.length} giọng đọc khả dụng`
                : `${filteredClonedVoices.length} giọng clone cá nhân`}
            </span>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-control bg-slate-200 hover:bg-slate-300 dark:bg-white/10 dark:hover:bg-white/20 text-slate-800 dark:text-white text-xs font-semibold transition-colors"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>

      {/* Voice Clone Creation Modal */}
      <VoiceCloneModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        onVoiceCreated={handleVoiceCloneCreated}
      />
    </>
  )
}
