import { useState, useMemo } from 'react'
import { Search, Star, Play, Check, X, Sparkles } from 'lucide-react'
import type { Voice } from '../../api/tts'

interface VoicePickerProps {
  isOpen: boolean
  onClose: () => void
  voices: Voice[]
  selectedVoiceId: string
  onSelectVoice: (voiceId: string) => void
  onPreviewSample?: (voiceId: string) => void
}

export default function VoicePicker({
  isOpen,
  onClose,
  voices,
  selectedVoiceId,
  onSelectVoice,
  onPreviewSample,
}: VoicePickerProps) {
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

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const next = favorites.includes(id)
      ? favorites.filter((fav) => fav !== id)
      : [...favorites, id]
    setFavorites(next)
    localStorage.setItem('voxify_favorite_voices', JSON.stringify(next))
  }

  const filteredVoices = useMemo(() => {
    return voices.filter((v) => {
      // Lọc ngôn ngữ
      if (langFilter === 'vi' && !v.locale.toLowerCase().startsWith('vi')) {
        return false
      }
      // Lọc giới tính
      if (genderFilter !== 'all' && v.gender.toLowerCase() !== genderFilter.toLowerCase()) {
        return false
      }
      // Lọc tìm kiếm
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

  if (!isOpen) return null

  return (
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
                Tìm kiếm và chọn giọng đọc tự nhiên cho nội dung của bạn
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
                    {/* Avatar */}
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
                    {/* Nút nghe thử */}
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

                    {/* Nút yêu thích */}
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

                    {/* Checkmark nếu đang chọn */}
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

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#0B0D12] flex items-center justify-between text-xs text-slate-500 dark:text-white/40">
          <span>{filteredVoices.length} giọng đọc khả dụng</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-control bg-slate-200 hover:bg-slate-300 dark:bg-white/10 dark:hover:bg-white/20 text-slate-800 dark:text-white text-xs font-semibold transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  )
}
