import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useVoiceLibrary, useToggleFavorite } from '../hooks/useVoiceLibrary'
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
  deleteClonedVoice,
  getVoiceCloneLimits,
  type ClonedVoice,
  type VoiceCloneQuota,
} from '../api/voice_clone'
import type { VoiceLibraryItem } from '../api/voice_library'
import VoiceCloneModal from '../components/studio/VoiceCloneModal'

export default function VoiceLibrary() {
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab')
  const activeTab: 'all' | 'mine' | 'favorites' =
    tabParam === 'mine' || tabParam === 'cloned'
      ? 'mine'
      : tabParam === 'favorites'
      ? 'favorites'
      : 'all'

  const [search, setSearch] = useState('')
  const [langFilter, setLangFilter] = useState<'vi' | 'all'>('vi')
  const [genderFilter, setGenderFilter] = useState<'all' | 'Female' | 'Male'>('all')

  // Quota & clone modal
  const [clonedQuota, setClonedQuota] = useState<VoiceCloneQuota | null>(null)
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false)
  const [deletingVoiceId, setDeletingVoiceId] = useState<string | null>(null)

  // Audio preview
  const [playingPreviewId, setPlayingPreviewId] = useState<number | null>(null)
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null)

  // React Query library query
  const { data, isLoading, refetch } = useVoiceLibrary({
    tab: activeTab,
    language: langFilter === 'vi' ? 'vi' : undefined,
    gender: genderFilter === 'all' ? undefined : genderFilter,
    search: search.trim() || undefined,
  })

  const toggleFavoriteMutation = useToggleFavorite()

  const voices = data?.voices ?? []

  useEffect(() => {
    if (activeTab === 'mine') {
      getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
    }
  }, [activeTab])

  useEffect(() => {
    return () => {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause()
        audioPreviewRef.current = null
      }
    }
  }, [])

  const setTab = (tab: 'all' | 'mine' | 'favorites') => {
    if (tab === 'all') {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause()
      audioPreviewRef.current = null
      setPlayingPreviewId(null)
    }
  }

  const handleToggleFavorite = async (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await toggleFavoriteMutation.mutateAsync(voice.id)
      toast.info(res.is_favorite ? 'Đã thêm vào yêu thích' : 'Đã bỏ yêu thích')
    } catch {
      toast.error('Không thể cập nhật danh sách yêu thích.')
    }
  }

  const handlePlayPreview = (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    if (playingPreviewId === voice.id) {
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

    // Determine audio source
    let previewSrc = voice.preview_url
    if (!previewSrc && voice.voice_type === 'cloned' && voice.cloned_voice_ref) {
      previewSrc = `/api/voices/cloned/${voice.cloned_voice_ref}/preview`
    } else if (!previewSrc && voice.provider_voice_id) {
      previewSrc = `/api/tts/sample?voice=${encodeURIComponent(voice.provider_voice_id)}`
    }

    if (!previewSrc) {
      toast.info('Không có bản nghe thử khả dụng cho giọng này.')
      return
    }

    const audio = new Audio(previewSrc)
    audioPreviewRef.current = audio
    setPlayingPreviewId(voice.id)

    audio.onended = () => {
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    }

    audio.onerror = () => {
      toast.error('Không thể phát bản nghe thử của giọng này.')
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    }

    audio.play().catch(() => {
      setPlayingPreviewId(null)
      audioPreviewRef.current = null
    })
  }

  const handleDeleteClonedVoice = async (voice: VoiceLibraryItem, e: React.MouseEvent) => {
    e.stopPropagation()
    const targetRef = voice.cloned_voice_ref || voice.provider_voice_id
    if (!targetRef) return

    const confirm = window.confirm(
      `Bạn có chắc chắn muốn xóa vĩnh viễn giọng clone "${voice.name}"? Tệp âm thanh mẫu và bản nghe thử sẽ bị xóa hoàn toàn.`
    )
    if (!confirm) return

    setDeletingVoiceId(targetRef)
    try {
      await deleteClonedVoice(targetRef)
      toast.success(`Đã xóa thành công giọng clone "${voice.name}"`)
      refetch()
      getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
    } catch {
      toast.error('Xóa giọng clone thất bại, vui lòng thử lại sau.')
    } finally {
      setDeletingVoiceId(null)
    }
  }

  const handleVoiceCloneCreated = (_newVoice: ClonedVoice) => {
    toast.success(`Đã tạo thành công giọng clone "${_newVoice.name}"!`)
    setIsCloneModalOpen(false)
    setTab('mine')
    refetch()
    getVoiceCloneLimits().then(setClonedQuota).catch(() => {})
  }

  const handleUseVoice = (voice: VoiceLibraryItem) => {
    const voiceParam = voice.provider_voice_id || voice.name
    navigate(`/studio?voice=${encodeURIComponent(voiceParam)}`)
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
          {activeTab === 'mine' ? (
            <button
              onClick={() => setIsCloneModalOpen(true)}
              className="px-4 py-2 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/25 flex items-center gap-2 transition-transform active:scale-95"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Tạo giọng clone mới</span>
            </button>
          ) : (
            <span className="text-xs font-mono px-3 py-1.5 rounded-control bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-indigo-700 dark:text-indigo-400 font-semibold shadow-xs">
              {voices.length} giọng sẵn sàng
            </span>
          )}
        </div>
      </div>

      {/* 3 Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-white/[0.08] pb-1">
        <button
          onClick={() => setTab('all')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-control transition-all ${
            activeTab === 'all'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Tất cả</span>
        </button>

        <button
          onClick={() => setTab('mine')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-control transition-all ${
            activeTab === 'mine'
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
          }`}
        >
          <Mic className="w-4 h-4 text-purple-400" />
          <span>Giọng của tôi</span>
          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-white/20 text-white">
            Clone
          </span>
        </button>

        <button
          onClick={() => setTab('favorites')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-control transition-all ${
            activeTab === 'favorites'
              ? 'bg-amber-500 text-white shadow-xs'
              : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5'
          }`}
        >
          <Star className="w-4 h-4 fill-current text-amber-300" />
          <span>Yêu thích</span>
        </button>
      </div>

      {/* Quota Banner when on 'mine' tab */}
      {activeTab === 'mine' && (
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
                'Clone giọng đọc của bạn từ mẫu âm thanh (5 giây – 3 phút) để sử dụng trong AI Studio.'
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
      )}

      {/* Filters Bar */}
      <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 dark:text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên giọng đọc..."
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
        <div className="py-24 flex flex-col items-center justify-center gap-3 text-xs text-slate-400 dark:text-white/40">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          <span>Đang tải danh sách giọng đọc...</span>
        </div>
      ) : voices.length === 0 ? (
        <div className="py-20 px-4 text-center rounded-card border-2 border-dashed border-slate-300 dark:border-white/10 flex flex-col items-center justify-center gap-3">
          {activeTab === 'mine' ? (
            <>
              <div className="w-16 h-16 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                <Mic className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Bạn chưa có giọng clone nào
              </h3>
              <p className="text-xs text-slate-500 dark:text-white/50 max-w-md">
                Ghi âm trực tiếp hoặc tải lên tệp âm thanh (5s – 3 phút) giọng thật của bạn để tạo phiên bản AI độc quyền dùng trong Studio.
              </p>
              <button
                onClick={() => setIsCloneModalOpen(true)}
                className="mt-2 px-5 py-2.5 rounded-control bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-2 transition-transform active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Bắt đầu nhân bản giọng nói</span>
              </button>
            </>
          ) : activeTab === 'favorites' ? (
            <>
              <div className="w-16 h-16 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center">
                <Star className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Chưa có giọng yêu thích nào
              </h3>
              <p className="text-xs text-slate-500 dark:text-white/50 max-w-md">
                Bấm vào biểu tượng ngôi sao trên bất kỳ giọng đọc nào để lưu lại danh sách yêu thích của bạn.
              </p>
            </>
          ) : (
            <p className="text-xs text-slate-400 dark:text-white/40">
              Không tìm thấy giọng đọc nào phù hợp với bộ lọc hiện tại.
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {voices.map((voice) => {
            const isPlaying = playingPreviewId === voice.id
            const isCloned = voice.voice_type === 'cloned'
            const isDeleting = deletingVoiceId === (voice.cloned_voice_ref || voice.provider_voice_id)

            return (
              <div
                key={voice.id}
                className={`p-4 rounded-card bg-white dark:bg-[#12151C] border shadow-xs hover:shadow-md transition-all flex flex-col justify-between group ${
                  isCloned
                    ? 'border-purple-500/30 hover:border-purple-500'
                    : 'border-slate-200/80 dark:border-white/[0.08] hover:border-indigo-500/40'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
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
                      <div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                            {voice.display_name || voice.name}
                          </h3>
                          {isCloned ? (
                            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                              Clone
                            </span>
                          ) : (
                            <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-white/60">
                              {voice.provider}
                            </span>
                          )}
                          {voice.tier === 'premium' && (
                            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                              Pro
                            </span>
                          )}
                          {voice.credit_multiplier > 1.0 && (
                            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                              {voice.credit_multiplier}x
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-white/40 mt-0.5">
                          {voice.language} &middot; {voice.gender === 'Female' ? 'Nữ' : voice.gender === 'Male' ? 'Nam' : 'Khác'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      {/* Play Preview button */}
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

                      {/* Favorite button */}
                      <button
                        onClick={(e) => handleToggleFavorite(voice, e)}
                        className={`p-1.5 rounded-control transition-colors ${
                          voice.is_favorite
                            ? 'text-amber-500'
                            : 'text-slate-300 dark:text-white/20 hover:text-amber-500 hover:bg-slate-100 dark:hover:bg-white/5'
                        }`}
                        title={voice.is_favorite ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
                      >
                        <Star className={`w-3.5 h-3.5 ${voice.is_favorite ? 'fill-current' : ''}`} />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-white/60 mt-3 line-clamp-2">
                    {voice.description || (isCloned ? 'Giọng đọc AI clone cá nhân.' : 'Giọng đọc AI tiêu chuẩn chất lượng cao.')}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
                  {isCloned && activeTab === 'mine' ? (
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
                  ) : (
                    <span className="text-[10px] text-slate-400 dark:text-white/40">
                      Đã dùng: {voice.total_uses} lượt
                    </span>
                  )}

                  <button
                    onClick={() => handleUseVoice(voice)}
                    className={`px-3 py-1.5 rounded-control text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      isCloned
                        ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-xs'
                        : 'bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-600 dark:hover:bg-indigo-600 text-indigo-600 dark:text-indigo-400 hover:text-white dark:hover:text-white'
                    }`}
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

      {/* Voice Clone Modal */}
      <VoiceCloneModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        onVoiceCreated={handleVoiceCloneCreated}
      />
    </div>
  )
}
