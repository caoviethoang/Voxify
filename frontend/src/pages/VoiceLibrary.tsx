import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVoices } from '../hooks/useVoices'
import { useToast } from '../hooks/useToast'
import { Search, Star, Play, Volume2, ArrowRight } from 'lucide-react'

export default function VoiceLibrary() {
  const { data: voiceData, isLoading } = useVoices()
  const toast = useToast()
  const navigate = useNavigate()

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

  const voices = voiceData?.voices ?? []

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const next = favorites.includes(id)
      ? favorites.filter((fav) => fav !== id)
      : [...favorites, id]
    setFavorites(next)
    localStorage.setItem('voxify_favorite_voices', JSON.stringify(next))
    toast.info(next.includes(id) ? 'Đã thêm vào yêu thích' : 'Đã bỏ yêu thích')
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
            Khám phá hơn 300+ giọng đọc chất lượng phòng thu, tối ưu hóa cho tiếng Việt tự nhiên và đa ngôn ngữ.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-3 py-1.5 rounded-control bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-indigo-700 dark:text-indigo-400 font-semibold shadow-xs">
            {filteredVoices.length} giọng đọc sẵn sàng
          </span>
        </div>
      </div>

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

      {/* Grid danh sách giọng */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] animate-pulse space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-control bg-slate-200 dark:bg-white/5" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-4 w-1/2 bg-slate-200 dark:bg-white/5 rounded" />
                  <div className="h-3 w-1/3 bg-slate-200 dark:bg-white/5 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVoices.map((voice) => {
            const isFav = favorites.includes(voice.id)
            const isFemale = voice.gender.toLowerCase() === 'female'

            return (
              <div
                key={voice.id}
                className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/40 shadow-xs hover:shadow-md transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-10 h-10 rounded-control flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                          isFemale
                            ? 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20'
                            : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
                        }`}
                      >
                        {isFemale ? '♀' : '♂'}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">{voice.name}</h3>
                          {voice.locale.toLowerCase().startsWith('vi') && (
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-500/30">
                              VN
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-white/40 truncate">
                          {voice.locale_name || (isFemale ? 'Giọng Nữ' : 'Giọng Nam')}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => toggleFavorite(voice.id, e)}
                      className={`p-1.5 rounded-control transition-colors ${
                        isFav ? 'text-[#F59E0B]' : 'text-slate-300 dark:text-white/30 hover:text-[#F59E0B]'
                      }`}
                      title={isFav ? 'Bỏ yêu thích' : 'Yêu thích'}
                    >
                      <Star className={`w-4 h-4 ${isFav ? 'fill-current' : ''}`} />
                    </button>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-white/50 line-clamp-2 leading-relaxed">
                    Giọng đọc tự nhiên chất lượng cao từ engine Edge-TTS với khả năng biểu cảm phong phú.
                  </p>
                </div>

                <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-100 dark:border-white/[0.04]">
                  <button
                    onClick={() => toast.info(`Đang nghe thử giọng ${voice.name}`)}
                    className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 dark:text-white/60 dark:hover:text-white transition-colors"
                  >
                    <Play className="w-3.5 h-3.5 fill-current text-indigo-600 dark:text-indigo-400" />
                    <span>Nghe mẫu</span>
                  </button>

                  <button
                    onClick={() => handleUseVoice(voice.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white dark:bg-indigo-600/20 dark:hover:bg-indigo-600 dark:text-indigo-300 dark:hover:text-white text-xs font-semibold transition-all border border-indigo-200/80 dark:border-indigo-500/30"
                  >
                    <span>Dùng giọng này</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
