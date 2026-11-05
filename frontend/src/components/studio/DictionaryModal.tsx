import { useState, useEffect, useCallback } from 'react'
import {
  X,
  Plus,
  Trash2,
  BookA,
  Search,
  Check,
  Volume2,
  Filter,
  Sparkles,
} from 'lucide-react'
import {
  listDictionaryRules,
  createDictionaryRule,
  updateDictionaryRule,
  deleteDictionaryRule,
  type DictionaryRule,
} from '../../api/dictionary'
import { synthesize } from '../../api/tts'
import { useToast } from '../../hooks/useToast'

interface DictionaryModalProps {
  isOpen: boolean
  onClose: () => void
  currentVoice?: string
}

export default function DictionaryModal({ isOpen, onClose, currentVoice = 'vi-VN-HoaiMyNeural' }: DictionaryModalProps) {
  const toast = useToast()
  const [rules, setRules] = useState<DictionaryRule[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState<string>('all')

  // Form thêm từ mới
  const [word, setWord] = useState('')
  const [replacement, setReplacement] = useState('')
  const [category, setCategory] = useState<'abbreviation' | 'date' | 'number' | 'name' | 'custom'>('abbreviation')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Audio test phát âm
  const [testingWordId, setTestingWordId] = useState<number | null>(null)

  const loadRules = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await listDictionaryRules()
      setRules(data)
    } catch {
      toast.error('Không thể tải danh sách từ điển.')
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  useEffect(() => {
    if (isOpen) {
      loadRules()
    }
  }, [isOpen, loadRules])

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!word.trim() || !replacement.trim()) {
      toast.error('Vui lòng nhập cả từ gốc và cách đọc thay thế.')
      return
    }

    setIsSubmitting(true)
    try {
      const created = await createDictionaryRule({
        word: word.trim(),
        replacement: replacement.trim(),
        category,
      })
      setRules([created, ...rules])
      setWord('')
      setReplacement('')
      toast.success(`Đã thêm quy tắc cho "${created.word}"!`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Lỗi khi thêm từ'
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleToggle = async (id: number, currentActive: boolean) => {
    try {
      const updated = await updateDictionaryRule(id, { is_active: !currentActive })
      setRules(rules.map((r) => (r.id === id ? updated : r)))
      toast.info(`Đã ${!currentActive ? 'bật' : 'tắt'} quy tắc phát âm.`)
    } catch {
      toast.error('Không thể cập nhật quy tắc.')
    }
  }

  const handleDelete = async (id: number, wordName: string) => {
    try {
      await deleteDictionaryRule(id)
      setRules(rules.filter((r) => r.id !== id))
      toast.success(`Đã xóa quy tắc cho "${wordName}".`)
    } catch {
      toast.error('Không thể xóa quy tắc.')
    }
  }

  const handleTestPronounce = async (id: number, textToSpeak: string) => {
    setTestingWordId(id)
    try {
      const blob = await synthesize({
        text: textToSpeak,
        voice: currentVoice,
        rate: '+0%',
        pitch: '+0Hz',
        volume: '+0%',
        preview: true,
      })
      const audioUrl = URL.createObjectURL(blob)
      const audio = new Audio(audioUrl)
      audio.onended = () => {
        setTestingWordId(null)
        URL.revokeObjectURL(audioUrl)
      }
      await audio.play()
    } catch {
      toast.error('Không thể phát âm thử.')
      setTestingWordId(null)
    }
  }

  const filteredRules = rules.filter((r) => {
    const matchSearch =
      r.word.toLowerCase().includes(search.toLowerCase()) ||
      r.replacement.toLowerCase().includes(search.toLowerCase())
    const matchCategory = filterCategory === 'all' || r.category === filterCategory
    return matchSearch && matchCategory
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-card shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header Modal */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-white/[0.08]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-control bg-indigo-500/10 text-indigo-500">
              <BookA className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Từ điển phát âm cá nhân
              </h2>
              <p className="text-xs text-slate-500 dark:text-white/40">
                Tự động thay thế từ viết tắt, số, ngày tháng hoặc tên riêng trước khi đọc
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-control text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form thêm quy tắc mới */}
        <form onSubmit={handleAddRule} className="p-5 border-b border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02]">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
            <div className="sm:col-span-4">
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-white/60 mb-1">
                Từ gốc (Cần sửa)
              </label>
              <input
                type="text"
                placeholder="VD: TP.HCM, AI, CEO"
                value={word}
                onChange={(e) => setWord(e.target.value)}
                className="w-full bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] rounded-control px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="sm:col-span-4">
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-white/60 mb-1">
                Cách đọc thay thế
              </label>
              <input
                type="text"
                placeholder="VD: Thành phố Hồ Chí Minh"
                value={replacement}
                onChange={(e) => setReplacement(e.target.value)}
                className="w-full bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] rounded-control px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-white/60 mb-1">
                Phân loại
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as any)}
                className="w-full bg-white dark:bg-[#181C25] border border-slate-200 dark:border-white/[0.1] rounded-control px-2 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="abbreviation">Viết tắt</option>
                <option value="name">Tên riêng</option>
                <option value="number">Số</option>
                <option value="date">Ngày tháng</option>
                <option value="custom">Tùy chỉnh</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-all"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm</span>
              </button>
            </div>
          </div>
        </form>

        {/* Tìm kiếm & Lọc */}
        <div className="px-5 py-3 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between gap-3 bg-white dark:bg-[#12151C]">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Tìm kiếm từ trong từ điển..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-100 dark:bg-[#181C25] border border-transparent dark:border-white/[0.05] rounded-control text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-white/50">
            <Filter className="w-3.5 h-3.5" />
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="bg-slate-100 dark:bg-[#181C25] border-none rounded-control px-2 py-1 text-xs text-slate-800 dark:text-white/80 focus:outline-none"
            >
              <option value="all">Tất cả loại ({rules.length})</option>
              <option value="abbreviation">Từ viết tắt</option>
              <option value="name">Tên riêng</option>
              <option value="number">Số</option>
              <option value="date">Ngày tháng</option>
              <option value="custom">Tùy chỉnh</option>
            </select>
          </div>
        </div>

        {/* Danh sách các quy tắc */}
        <div className="flex-1 overflow-y-auto p-5 space-y-2">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-400">Đang tải dữ liệu từ điển...</div>
          ) : filteredRules.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              {search ? 'Không tìm thấy quy tắc phù hợp với tìm kiếm.' : 'Chưa có quy tắc nào. Hãy thêm từ đầu tiên phía trên!'}
            </div>
          ) : (
            filteredRules.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between p-3 rounded-control bg-slate-50 dark:bg-[#181C25] border border-slate-200/80 dark:border-white/[0.05] hover:border-indigo-500/30 transition-all"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => handleToggle(r.id, r.is_active)}
                    className={`w-5 h-5 rounded-md flex items-center justify-center transition-colors ${
                      r.is_active
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-200 dark:bg-white/10 text-transparent hover:bg-slate-300 dark:hover:bg-white/20'
                    }`}
                    title={r.is_active ? 'Đang kích hoạt (Bấm để tắt)' : 'Đã tắt (Bấm để bật)'}
                  >
                    <Check className="w-3 h-3 stroke-[3]" />
                  </button>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-slate-900 dark:text-white truncate">
                        {r.word}
                      </span>
                      <span className="text-[10px] text-slate-400">→</span>
                      <span className="font-medium text-xs text-indigo-600 dark:text-indigo-400 truncate">
                        {r.replacement}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                      {r.category === 'abbreviation'
                        ? 'Viết tắt'
                        : r.category === 'name'
                        ? 'Tên riêng'
                        : r.category === 'number'
                        ? 'Số'
                        : r.category === 'date'
                        ? 'Ngày tháng'
                        : 'Tùy chỉnh'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTestPronounce(r.id, r.replacement)}
                    disabled={testingWordId === r.id}
                    className="p-1.5 rounded-control text-slate-400 hover:text-indigo-500 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                    title="Phát âm thử cách đọc"
                  >
                    <Volume2 className={`w-3.5 h-3.5 ${testingWordId === r.id ? 'animate-bounce text-indigo-500' : ''}`} />
                  </button>

                  <button
                    onClick={() => handleDelete(r.id, r.word)}
                    className="p-1.5 rounded-control text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                    title="Xóa quy tắc"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-white/[0.08] flex items-center justify-between text-xs text-slate-500 dark:text-white/40">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span>Áp dụng tự động khi bấm &quot;Tạo giọng nói&quot;</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-control bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 text-slate-800 dark:text-white text-xs font-semibold transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  )
}
