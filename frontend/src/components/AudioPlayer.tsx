import { useRef, useEffect } from 'react'

interface Props {
  url: string | null
  voiceName: string
  isPreview: boolean
  onDownload: () => void
}

export default function AudioPlayer({ url, voiceName, isPreview, onDownload }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (url && audioRef.current) {
      audioRef.current.src = url
      audioRef.current.play().catch(() => {})
    }
  }, [url])

  if (!url) return null

  return (
    <div className="bg-brand-500/5 border border-brand-500/15 rounded-2xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-400/20 px-2 py-0.5 rounded-full shrink-0">
            Audio sẵn sàng
          </span>
          <span className="text-xs text-white/50 truncate">
            {voiceName}{isPreview ? ' · [Nghe thử]' : ''}
          </span>
        </div>
        <button
          onClick={onDownload}
          className="flex items-center gap-1.5 text-xs font-medium border border-white/10 hover:border-brand-500/40 text-white/60 hover:text-brand-400 px-3 py-1.5 rounded-lg transition-all shrink-0"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Tải MP3
        </button>
      </div>
      <audio ref={audioRef} controls className="w-full h-9 rounded-lg" style={{ colorScheme: 'dark' }} />
    </div>
  )
}
