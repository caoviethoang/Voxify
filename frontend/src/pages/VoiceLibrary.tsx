import { useState, useMemo, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useVoices } from '../hooks/useVoices'
import { useToast } from '../hooks/useToast'
import {
  Search,
  Star,
  Play,
  Pause,
  Volume2,
  ArrowRight,
  Mic,
  Sparkles,
  Plus,
  Trash2,
  Loader2,
  Layers,
} from 'lucide-react'
import {
  listClonedVoices,
  deleteClonedVoice,
  getVoiceCloneLimits,
  type ClonedVoice,
  type VoiceCloneQuota,
} from '../api/voice_clone'
import VoiceCloneModal from '../components/studio/VoiceCloneModal'

export default function VoiceLibrary() {
  const { data: voiceData, isLoading } = useVoices()
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const currentTab = searchParams.get('tab') === 'cloned' ? 'cloned' : 'system'

  const [search, setSearch] = useState('')
  const [langFilter, setLangFilter] = useState<'vi' | 'all'>('vi')
  const [genderFilter, setGenderFilter] = useState<'all' | 'Female' | 'Male'>('all')
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
  const [playingPreviewId, setPlayingPreviewId] = useState<string | null>(null)
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null)

  const voices = voiceData?.voices ?? []

  const fetchClonedData = async () => {
    setIsLoadingCloned(true)
    try {
      const [listRes, quotaRes] = await Promise.all([
        listClonedVoices(),
        getVoiceCloneLimits().catch(() => null),
      ])
      setClonedVoices(listRes.voices || [])
      if (quotaRes) setClonedQuota(quotaRes)
    } catch {
      // offline / unauthenticated fallback
    } finally {
      setIsLoadingCloned(false)
    }
  }

  useEffect(() => {
    fetchClonedData()
    return () => {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
      }
    }
  }, [])

  const setTab = (tab: 'system' | 'cloned') => {
    if (tab === 'cloned') {
      setSearchParams({ tab: 'cloned' })
    } else {
      setSearchParams({})
    }
  }

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const next = favorites.includes(id)
      ? favorites.filter((fav) => fav !== id)
      : [...favorites, id]
    setFavorites(next)
    localStorage.setItem('voxify_favorite_voices', JSON.stringify(next))
    toast.info(next.includes(id) ? 'Đã thêm vào yêu thích' : 'Đã bỏ yêu thích')
  }

  const handlePlayClonedPreview = (voice: ClonedVoice, e: React.MouseEvent) => {
    e.stopPropagation()
    if (playingPreviewId === voice.voice_id) {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
      }
      setPlayingPreviewId(null)
      return
    }

    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause()
    }

    const previewSrc =
      voice.preview_audio_url || voice.preview_url || `/api/voices/cloned/${voice.voice_id}/preview`
    const audio = new Audio(previewSrc)
    audioPreviewRef.current = audio
    setPlayingPreviewId(voice.voice_id)

    audio.onended = () => {
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    }

    audio.onerror = () => {
      toast.error('Không thể phát bản nghe thử của giọng clone này.')
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    }

    audio.play().catch(() => {
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    })
  }

  const handleDeleteClonedVoice = async (voice: ClonedVoice, e: React.MouseEvent) => {
    e.stopPropagation()
    const confirm = window.confirm(
      `Bạn có chắc chắn muốn xóa vĩnh viễn giọng clone "${voice.name}"? Tệp âm thanh mẫu và bản nghe thử sẽ bị xóa hoàn toàn.`
    )
    if (!confirm) return

    setDeletingVoiceId(voice.voice_id)
    try {
      await deleteClonedVoice(voice.voice_id)
      toast.success(`Đã xóa thành công giọng clone "${voice.name}"`)
      setClonedVoices((prev) => prev.filter((v) => v.voice_id !== voice.voice_id))
      getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
    } catch {
      toast.error('Xóa giọng clone thất bại, vui lòng thử lại sau.')
    } finally {
      setDeletingVoiceId(null)
    }
  }

  const handleVoiceCloneCreated = (newVoice: ClonedVoice) => {
    setClonedVoices((prev) => [newVoice, ...prev])
    toast.success(`Đã tạo thành công giọng clone "${newVoice.name}"!`)
    setIsCloneModalOpen(false)
    setTab('cloned')
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
        return (
          v.name.toLowerCase().includes(q) ||
          v.full_name?.toLowerCase().includes(q) ||
          v.locale_name?.toLowerCase().includes(q)
        )
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

  const handleUseVoice = (voiceId: string) => {
    navigate(`/studio?voice=${voiceId}`)
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto py-2 animate-in fade-in duration-150">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Volume2 className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            <span>Thư viện Giọng đọc AI</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1">
            Khám phá hơn 300+ giọng đọc chất lượng phòng thu hoặc tự nhân bản giọng đọc AI cá nhân của bạn.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {currentTab === 'cloned' ? (
            <button
              onClick={() => setIsCloneModalOpen(true)}
              className="px-4 py-2 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/25 flex items-center gap-2 transition-transform active:scale-95"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Tạo giọng clone mới</span>
            </button>
          ) : (
            <span className="text-xs font-mono px-3 py-1.5 rounded-control bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-indigo-700 dark:text-indigo-400 font-semibold shadow-xs">
              {filteredVoices.length} giọng hệ thống sẵn sàng
            </span>
          )}
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-white/[0.08] pb-1">
        <button
          onClick={() => setTab('system')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-control transition-all ${
            currentTab === 'system'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Thư viện hệ thống ({voices.length})</span>
        </button>

        <button
          onClick={() => setTab('cloned')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-control transition-all ${
            currentTab === 'cloned'
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
          }`}
        >
          <Mic className="w-4 h-4 text-purple-400" />
          <span>Giọng của tôi ({clonedVoices.length})</span>
          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-white/20 text-white">
            Clone
          </span>
        </button>
      </div>

      {/* TAB 1: THƯ VIỆN HỆ THỐNG */}
      {currentTab === 'system' && (
        <>
          {/* Bộ lọc & Tìm kiếm */}
          <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
            {/* Search */}
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-slate-400 dark:text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm theo tên, vùng miền..."
                className="w-full bg-slate-50 dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.08] rounded-control pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-white/30 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              {/* Lang Filter */}
              <div className="flex bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08] text-xs">
                <button
                  onClick={() => setLangFilter('vi')}
                  className={`px-3 py-1 rounded-[8px] font-semibold transition-all ${
                    langFilter === 'vi'
                      ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Tiếng Việt
                </button>
                <button
                  onClick={() => setLangFilter('all')}
                  className={`px-3 py-1 rounded-[8px] font-semibold transition-all ${
                    langFilter === 'all'
                      ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Tất cả
                </button>
              </div>

              {/* Gender Filter */}
              <div className="flex bg-slate-100 dark:bg-[#181C25] p-0.5 rounded-control border border-slate-200 dark:border-white/[0.08] text-xs">
                <button
                  onClick={() => setGenderFilter('all')}
                  className={`px-2.5 py-1 rounded-[8px] font-medium transition-all ${
                    genderFilter === 'all'
                      ? 'bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Tất cả
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

          {/* Voices Grid */}
          {isLoading ? (
            <div className="py-24 text-center text-xs text-slate-400 dark:text-white/40">
              Đang tải danh sách giọng đọc...
            </div>
          ) : filteredVoices.length === 0 ? (
            <div className="py-24 text-center text-xs text-slate-400 dark:text-white/40">
              Không tìm thấy giọng đọc nào phù hợp.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredVoices.map((voice) => {
                const isFav = favorites.includes(voice.id)

                return (
                  <div
                    key={voice.id}
                    className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200/80 dark:border-white/[0.08] hover:border-indigo-500/40 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-10 h-10 rounded-control flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                              voice.gender.toLowerCase() === 'female'
                                ? 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20'
                                : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
                            }`}
                          >
                            {voice.gender.toLowerCase() === 'female' ? '♀' : '♂'}
                          </div>
                          <div>
                            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                              {voice.name}
                            </h3>
                            <p className="text-[11px] text-slate-500 dark:text-white/40">
                              {voice.locale_name || voice.locale}
                            </p>
                          </div>
                        </div>

                        <button
                          onClick={(e) => toggleFavorite(voice.id, e)}
                          className={`p-1.5 rounded-control transition-colors ${
                            isFav
                              ? 'text-[#F59E0B]'
                              : 'text-slate-300 dark:text-white/20 hover:text-[#F59E0B] hover:bg-slate-100 dark:hover:bg-white/5'
                          }`}
                        >
                          <Star className={`w-4 h-4 ${isFav ? 'fill-current' : ''}`} />
                        </button>
                      </div>

                      <p className="text-xs text-slate-600 dark:text-white/60 mt-3 line-clamp-2">
                        {voice.full_name || 'Giọng đọc AI tiêu chuẩn chất lượng cao.'}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 dark:text-white/40">
                        {voice.gender.toLowerCase() === 'female' ? 'Nữ' : 'Nam'} &middot;{' '}
                        {voice.locale}
                      </span>

                      <button
                        onClick={() => handleUseVoice(voice.id)}
                        className="px-3 py-1.5 rounded-control bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-600 dark:hover:bg-indigo-600 text-indigo-600 dark:text-indigo-400 hover:text-white dark:hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-all"
                      >
                        <span>Sử dụng</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* TAB 2: GIỌNG CỦA TÔI (VOICE CLONING) */}
      {currentTab === 'cloned' && (
        <div className="space-y-4">
          {/* Quota Banner */}
          <div className="p-4 rounded-card bg-gradient-to-r from-purple-500/15 via-indigo-500/10 to-transparent border border-purple-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Quản lý Giọng đọc Clone cá nhân
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-700 dark:text-purple-300 border border-purple-500/30">
                  x1.5 Credit / lượt đọc
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-white/60 mt-1">
                {clonedQuota ? (
                  <>
                    Gói hiện tại: <strong>{clonedQuota.plan_name}</strong> &middot; Giới hạn:{' '}
                    <strong>
                      {clonedQuota.used} / {clonedQuota.max_allowed}
                    </strong>{' '}
                    giọng clone cá nhân.
                  </>
                ) : (
                  'Clone giọng đọc của bạn từ 5–30 giây mẫu âm thanh để sử dụng trong AI Studio.'
                )}
              </p>
            </div>

            <button
              onClick={() => setIsCloneModalOpen(true)}
              className="px-4 py-2.5 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-2 flex-shrink-0 transition-transform active:scale-95"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Tạo giọng clone mới</span>
            </button>
          </div>

          {/* Cloned Voices Grid */}
          {isLoadingCloned ? (
            <div className="py-24 flex flex-col items-center justify-center gap-3 text-xs text-slate-400 dark:text-white/40">
              <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
              <span>Đang tải danh sách giọng clone của bạn...</span>
            </div>
          ) : filteredClonedVoices.length === 0 ? (
            <div className="py-20 px-4 text-center rounded-card border-2 border-dashed border-slate-300 dark:border-white/10 flex flex-col items-center justify-center gap-3">
              <div className="w-16 h-16 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                <Mic className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Bạn chưa có giọng clone nào
              </h3>
              <p className="text-xs text-slate-500 dark:text-white/50 max-w-md">
                Ghi âm trực tiếp hoặc tải lên tệp âm thanh 5–30s giọng thật của bạn để tạo phiên bản AI độc quyền dùng trong Studio.
              </p>
              <button
                onClick={() => setIsCloneModalOpen(true)}
                className="mt-2 px-5 py-2.5 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-2 transition-transform active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Bắt đầu nhân bản giọng nói</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredClonedVoices.map((voice) => {
                const isPlaying = playingPreviewId === voice.voice_id
                const isDeleting = deletingVoiceId === voice.voice_id

                return (
                  <div
                    key={voice.voice_id}
                    className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-purple-500/30 hover:border-purple-500 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-control bg-gradient-to-br from-purple-500/20 to-indigo-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30 flex items-center justify-center font-bold text-sm">
                            ✨
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                {voice.name}
                              </h3>
                              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                                Clone
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-white/40 mt-0.5">
                              Mẫu: {voice.sample_duration ? `${voice.sample_duration.toFixed(1)}s` : '5-30s'} &middot;{' '}
                              <span className="text-amber-500 font-semibold">
                                ★ {voice.quality_score ? voice.quality_score.toFixed(1) : '5.0'}
                              </span>
                            </p>
                          </div>
                        </div>

                        {/* Nút nghe thử preview */}
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
                            <Pause className="w-4 h-4 fill-current" />
                          ) : (
                            <Play className="w-4 h-4 fill-current" />
                          )}
                        </button>
                      </div>

                      <p className="text-xs text-slate-600 dark:text-white/60 mt-3 line-clamp-2">
                        {voice.description || 'Giọng đọc AI clone cá nhân độc quyền của bạn.'}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
                      <button
                        disabled={isDeleting}
                        onClick={(e) => handleDeleteClonedVoice(voice, e)}
                        className="p-1.5 rounded-control text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors disabled:opacity-40"
                        title="Xóa giọng clone này"
                      >
                        {isDeleting ? (
                          <Loader2 className="w-4 h-4 animate-spin text-rose-500" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>

                      <button
                        onClick={() => handleUseVoice(voice.voice_id)}
                        className="px-3 py-1.5 rounded-control bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs"
                      >
                        <span>Dùng trong Studio</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Voice Clone Modal */}
      <VoiceCloneModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        onVoiceCreated={handleVoiceCloneCreated}
      />
    </div>
  )
}
