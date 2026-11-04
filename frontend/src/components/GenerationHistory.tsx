import type { HistoryItem } from '../hooks/useTTS'

interface Props {
  history: HistoryItem[]
  onReplay: (item: HistoryItem) => void
  onDownload: (item: HistoryItem) => void
  onClear: () => void
}

export default function GenerationHistory({ history, onReplay, onDownload, onClear }: Props) {
  return (
    <section className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="flex items-center gap-2 font-semibold text-sm">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
            </svg>
            Lịch sử phiên làm việc
          </h3>
          <p className="text-xs text-white/35 mt-0.5">Các bản ghi âm đã tạo trong phiên làm việc hiện tại của trình duyệt</p>
        </div>
        {history.length > 0 && (
          <button onClick={onClear} className="text-xs text-white/35 hover:text-red-400 transition-colors">
            Xóa toàn bộ lịch sử
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="bg-[#14141f] rounded-2xl border border-white/5 p-8 text-center">
          <svg className="mx-auto mb-3 text-white/15" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" />
          </svg>
          <p className="text-xs text-white/30">Chưa có bản ghi âm nào. Hãy nhập văn bản và bấm &quot;Tạo giọng nói&quot; hoặc &quot;Nghe thử&quot;!</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {history.map(item => {
            const snippet = item.text.length > 90 ? item.text.slice(0, 90) + '…' : item.text
            const timeStr = item.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            return (
              <div key={item.id} className="bg-[#14141f] border border-white/5 rounded-xl p-3.5 flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-white/70 italic truncate">&ldquo;{snippet}&rdquo;</div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="text-[11px] bg-white/5 text-white/50 px-1.5 py-0.5 rounded-md">{item.voiceName}</span>
                    {item.isPreview && (
                      <span className="text-[10px] bg-brand-500/15 text-brand-400 border border-brand-500/25 px-1.5 py-0.5 rounded-md">Nghe thử</span>
                    )}
                    <span className="text-[11px] text-white/35">Tốc độ: {item.rate}</span>
                    <span className="text-[11px] text-white/25">{timeStr}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => onReplay(item)}
                    className="flex items-center gap-1 text-xs border border-white/10 hover:border-brand-500/40 text-white/50 hover:text-brand-400 px-2.5 py-1.5 rounded-lg transition-all"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                    Phát
                  </button>
                  <button
                    onClick={() => onDownload(item)}
                    className="p-1.5 border border-white/10 hover:border-white/25 text-white/40 hover:text-white/70 rounded-lg transition-all"
                    title="Tải MP3"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
