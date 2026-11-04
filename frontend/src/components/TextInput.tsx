import { useRef } from 'react'
import clsx from 'clsx'

interface Props {
  value: string
  onChange: (v: string) => void
  maxChars: number
  chunkSize: number
}

const SAMPLE_TEXT =
  'Chào mừng bạn đến với phòng thu âm Text-to-Speech chất lượng cao! Hệ thống hỗ trợ xử lý ngữ điệu tự nhiên, mượt mà và tối ưu hóa chuyên sâu cho tiếng Việt. Bạn có thể dễ dàng điều chỉnh tốc độ đọc, cao độ và âm lượng để tạo nên giọng đọc hoàn hảo cho video, sách nói hay tài liệu học tập.'

export default function TextInput({ value, onChange, maxChars, chunkSize }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const len = value.length
  const pct = (len / maxChars) * 100
  const chunkCount = len <= chunkSize ? 1 : Math.ceil(len / chunkSize)

  return (
    <div className="bg-[#14141f] rounded-2xl border border-white/5 p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold text-sm text-white">Nội dung văn bản</h2>
          <p className="text-xs text-white/40 mt-0.5">Nhập đoạn văn bản bạn muốn chuyển thành giọng đọc tự nhiên</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => { onChange(SAMPLE_TEXT); ref.current?.focus() }}
            className="flex items-center gap-1.5 text-xs text-white/50 hover:text-brand-400 transition-colors px-2 py-1 rounded-lg hover:bg-brand-500/10"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            Văn bản mẫu
          </button>
          <button
            type="button"
            onClick={() => { onChange(''); ref.current?.focus() }}
            className="flex items-center gap-1.5 text-xs text-red-400/70 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-500/10"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            Xóa
          </button>
        </div>
      </div>

      {/* Textarea */}
      <textarea
        ref={ref}
        value={value}
        onChange={e => onChange(e.target.value)}
        maxLength={maxChars}
        rows={9}
        placeholder="Nhập hoặc dán nội dung văn bản tiếng Việt tại đây (tối đa 20.000 ký tự)..."
        className="w-full bg-[#0f0f1a] rounded-xl border border-white/5 p-4 text-sm text-white/90 placeholder:text-white/25 resize-none focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 transition-colors leading-relaxed"
      />

      {/* Footer: chunk info + counter */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs text-white/40">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>
            {len === 0
              ? '1 đoạn xử lý trực tiếp'
              : len <= chunkSize
              ? `1 đoạn (${len} ký tự)`
              : `Dài: ~${chunkCount} đoạn ghép tự động`}
          </span>
        </div>
        <div className={clsx('text-xs font-mono transition-colors', pct > 95 ? 'text-red-400' : pct > 85 ? 'text-amber-400' : 'text-white/40')}>
          {len.toLocaleString('vi-VN')} / {maxChars.toLocaleString('vi-VN')} ký tự
        </div>
      </div>
    </div>
  )
}
