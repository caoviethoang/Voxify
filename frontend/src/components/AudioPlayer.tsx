import { useRef, useEffect, useState } from 'react'
import { Download, FileText, Play, Pause, Sparkles } from 'lucide-react'

interface Props {
  url: string | null
  voiceName: string
  isPreview?: boolean
  duration?: number
  format?: 'mp3' | 'wav'
  srtUrl?: string
  vttUrl?: string
  onDownload?: () => void
}

function formatDuration(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export default function AudioPlayer({
  url,
  voiceName,
  isPreview = false,
  duration = 0,
  format = 'mp3',
  srtUrl,
  vttUrl,
  onDownload,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [playbackRate, setPlaybackRate] = useState(1.0)
  const [audioDuration, setAudioDuration] = useState(duration)

  useEffect(() => {
    if (url && audioRef.current) {
      audioRef.current.src = url
      audioRef.current.playbackRate = playbackRate
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false))
    }
  }, [url])

  useEffect(() => {
    if (duration > 0) {
      setAudioDuration(duration)
    }
  }, [duration])

  if (!url) return null

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {})
    }
  }

  const handleTimeUpdate = () => {
    if (!audioRef.current) return
    setCurrentTime(audioRef.current.currentTime)
    if (!duration && audioRef.current.duration) {
      setAudioDuration(audioRef.current.duration)
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    setCurrentTime(time)
    if (audioRef.current) {
      audioRef.current.currentTime = time
    }
  }

  const handleSpeedChange = () => {
    const speeds = [1.0, 1.25, 1.5, 2.0]
    const nextIdx = (speeds.indexOf(playbackRate) + 1) % speeds.length
    const nextSpeed = speeds[nextIdx]
    setPlaybackRate(nextSpeed)
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed
    }
  }

  const handleEnded = () => {
    setIsPlaying(false)
    setCurrentTime(0)
  }

  return (
    <div className="bg-white dark:bg-[#12151C] border border-indigo-200/80 dark:border-indigo-500/20 rounded-card p-4 shadow-sm flex flex-col gap-3 transition-all">
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        className="hidden"
      />

      {/* Header: Status badge, Voice Name, and Actions */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex items-center gap-1 text-[10px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full shrink-0">
            <Sparkles className="w-3 h-3 text-emerald-500" />
            Audio sẵn sàng
          </span>
          <span className="text-xs font-semibold text-slate-800 dark:text-white/90 truncate">
            {voiceName}
            {isPreview ? ' · [Nghe thử]' : ''}
          </span>
          <span className="hidden sm:inline-block text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-white/60">
            {format}
          </span>
        </div>

        {/* Action Buttons: Subtitles + Download */}
        <div className="flex items-center gap-1.5">
          {srtUrl && (
            <a
              href={srtUrl}
              download={`voxify_${Date.now()}.srt`}
              className="flex items-center gap-1 px-2.5 py-1 rounded-control bg-slate-100 hover:bg-slate-200 dark:bg-[#181C25] dark:hover:bg-[#202532] text-[11px] font-semibold text-slate-700 dark:text-white/80 border border-slate-200 dark:border-white/[0.08] transition-colors cursor-pointer"
              title="Tải phụ đề khớp thời gian chuẩn SRT"
            >
              <FileText className="w-3 h-3 text-indigo-500" />
              <span>SRT</span>
            </a>
          )}

          {vttUrl && (
            <a
              href={vttUrl}
              download={`voxify_${Date.now()}.vtt`}
              className="flex items-center gap-1 px-2.5 py-1 rounded-control bg-slate-100 hover:bg-slate-200 dark:bg-[#181C25] dark:hover:bg-[#202532] text-[11px] font-semibold text-slate-700 dark:text-white/80 border border-slate-200 dark:border-white/[0.08] transition-colors cursor-pointer"
              title="Tải phụ đề chuẩn WebVTT"
            >
              <FileText className="w-3 h-3 text-purple-500" />
              <span>VTT</span>
            </a>
          )}

          {onDownload ? (
            <button
              onClick={onDownload}
              className="flex items-center gap-1.5 px-3 py-1 rounded-control bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 text-[11px] font-bold text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/30 transition-colors shadow-xs"
            >
              <Download className="w-3 h-3" />
              <span>Tải {format.toUpperCase()}</span>
            </button>
          ) : (
            <a
              href={url}
              download={`voxify_${Date.now()}.${format}`}
              className="flex items-center gap-1.5 px-3 py-1 rounded-control bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 text-[11px] font-bold text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/30 transition-colors shadow-xs cursor-pointer"
            >
              <Download className="w-3 h-3" />
              <span>Tải {format.toUpperCase()}</span>
            </a>
          )}
        </div>
      </div>

      {/* Custom Player Controls */}
      <div className="flex items-center gap-3 bg-slate-50 dark:bg-[#0B0D12]/60 p-2.5 rounded-control border border-slate-100 dark:border-white/[0.06]">
        {/* Play/Pause Button */}
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white flex items-center justify-center shrink-0 shadow-sm transition-transform active:scale-95"
          title={isPlaying ? 'Tạm dừng' : 'Phát'}
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
        </button>

        {/* Time display */}
        <span className="text-[11px] font-mono text-slate-500 dark:text-white/50 shrink-0">
          {formatDuration(currentTime)}
        </span>

        {/* Seekbar */}
        <div className="flex-1 flex items-center relative">
          <input
            type="range"
            min={0}
            max={audioDuration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-1.5 bg-slate-200 dark:bg-[#181C25] rounded-lg appearance-none cursor-pointer accent-indigo-600"
          />
        </div>

        {/* Total Duration */}
        <span className="text-[11px] font-mono text-slate-500 dark:text-white/50 shrink-0">
          {formatDuration(audioDuration)}
        </span>

        {/* Speed button */}
        <button
          onClick={handleSpeedChange}
          className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-200/70 hover:bg-slate-300 dark:bg-white/10 dark:hover:bg-white/20 text-slate-700 dark:text-white/80 shrink-0 transition-colors"
          title="Tốc độ phát"
        >
          {playbackRate}x
        </button>
      </div>
    </div>
  )
}
