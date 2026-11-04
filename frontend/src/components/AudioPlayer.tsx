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
    <div className="bg-indigo-50/60 dark:bg-indigo-950/20 border border-indigo-200/60 dark:border-indigo-500/20 rounded-card p-4 flex flex-col gap-3 shadow-xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full shrink-0">
            Audio sẵn sàng
          </span>
          <span className="text-xs font-medium text-slate-700 dark:text-white/70 truncate">
            {voiceName}{isPreview ? ' · [Nghe thử]' : ''}
          </span>
        </div>
        <button
          onClick={onDownload}
          className="flex items-center gap-1.5 text-xs font-semibold border border-slate-200 dark:border-white/10 hover:border-indigo-500/40 text-slate-700 hover:text-indigo-600 dark:text-white/70 dark:hover:text-white bg-white dark:bg-white/5 hover:bg-slate-50 dark:hover:bg-white/10 px-3 py-1.5 rounded-control transition-all shrink-0 shadow-xs"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="19" x2="12" y2="3" />
          </svg>
          <span>Tải MP3</span>
        </button>
      </div>
      <audio ref={audioRef} controls className="w-full h-9 rounded-control" />
    </div>
  )
}
