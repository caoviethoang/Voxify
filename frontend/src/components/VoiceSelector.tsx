import { useState } from 'react'
import clsx from 'clsx'
import type { Voice } from '../api/tts'

type Filter = 'vietnamese' | 'all' | 'female' | 'male'

interface Props {
  voices: Voice[]
  total: number
  vietnameseCount: number
  selectedId: string
  onSelect: (id: string) => void
  isLoading: boolean
}

export default function VoiceSelector({ voices, total, vietnameseCount, selectedId, onSelect, isLoading }: Props) {
  const [filter, setFilter] = useState<Filter>('vietnamese')
  const [search, setSearch] = useState('')

  const filtered = voices.filter(v => {
    if (filter === 'vietnamese' && !v.is_vietnamese) return false
    if (filter === 'female' && v.gender.toLowerCase() !== 'female') return false
    if (filter === 'male' && v.gender.toLowerCase() !== 'male') return false
    if (search) {
      const q = search.toLowerCase()
      return (
        v.name.toLowerCase().includes(q) ||
        v.id.toLowerCase().includes(q) ||
        (v.locale_name ?? '').toLowerCase().includes(q) ||
        v.locale.toLowerCase().includes(q) ||
        (v.gender === 'Female' ? 'nữ' : 'nam').includes(q)
      )
    }
    return true
  })

  const tabs: { key: Filter; label: string }[] = [
    { key: 'vietnamese', label: 'Tiếng Việt' },
    { key: 'all', label: 'Tất cả' },
    { key: 'female', label: 'Nữ' },
    { key: 'male', label: 'Nam' },
  ]

  return (
    <div className="bg-[#14141f] rounded-2xl border border-white/5 p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="8" y1="22" x2="16" y2="22" />
          </svg>
          Giọng đọc
        </div>
        <span className="text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
          {isLoading ? 'Đang tải...' : `${vietnameseCount} giọng VN / ${total} tổng cộng`}
        </span>
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          type="text"
          placeholder="Tìm theo tên, ngôn ngữ, giới tính..."
          className="w-full bg-[#0f0f1a] border border-white/5 rounded-xl pl-8 pr-3 py-2 text-xs text-white/80 placeholder:text-white/25 focus:outline-none focus:border-brand-500/40 transition-colors"
        />
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={clsx(
              'flex-1 py-1.5 text-xs rounded-lg transition-all font-medium',
              filter === t.key
                ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                : 'text-white/40 hover:text-white/70 hover:bg-white/5'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Voice list */}
      <div className="flex flex-col gap-1 max-h-56 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-white/40">
            <div className="w-4 h-4 border-2 border-brand-500/50 border-t-brand-500 rounded-full animate-spin" />
            Đang tải danh sách giọng đọc...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-xs text-white/30">
            Không tìm thấy giọng đọc phù hợp.
          </div>
        ) : (
          filtered.map(v => {
            const isFemale = v.gender.toLowerCase() === 'female'
            const isSelected = v.id === selectedId
            return (
              <button
                key={v.id}
                onClick={() => onSelect(v.id)}
                className={clsx(
                  'flex items-center gap-3 p-2.5 rounded-xl text-left transition-all',
                  isSelected
                    ? 'bg-brand-500/15 border border-brand-500/30'
                    : 'hover:bg-white/5 border border-transparent'
                )}
              >
                <div className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 font-medium',
                  isFemale ? 'bg-pink-500/20 text-pink-400' : 'bg-blue-500/20 text-blue-400'
                )}>
                  {isFemale ? '♀' : '♂'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-white/90 truncate">{v.name}</div>
                  <div className="text-[11px] text-white/40 truncate">{v.locale_name || v.locale} · {isFemale ? 'Nữ' : 'Nam'}</div>
                </div>
                {v.is_vietnamese && (
                  <span className="shrink-0 text-[10px] font-medium bg-brand-500/20 text-brand-400 border border-brand-500/25 px-1.5 py-0.5 rounded-md">
                    Tiếng Việt
                  </span>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
