import React, { useState, useRef, useEffect, useCallback } from 'react'
import {
  Play,
  Pause,
  Upload,
  RefreshCw,
  ArrowRight,
  Volume2,
  FileAudio,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'
import type { AudioTool } from '../../api/audio_tools'

interface AudioWaveformWorkspaceProps {
  inputAudioUrl?: string | null
  outputAudioUrl?: string | null
  inputFileName?: string | null
  onFileSelect: (file: File) => void
  isProcessing?: boolean
  progress?: number
  isTrimMode?: boolean
  startTime?: number
  endTime?: number
  onTrimChange?: (start: number, end: number) => void
  availableTools?: AudioTool[]
  currentToolId?: string
  onChainToTool?: (targetToolId: string) => void
}

export const AudioWaveformWorkspace: React.FC<AudioWaveformWorkspaceProps> = ({
  inputAudioUrl,
  outputAudioUrl,
  inputFileName,
  onFileSelect,
  isProcessing = false,
  progress = 0,
  isTrimMode = false,
  startTime = 0,
  endTime = 0,
  onTrimChange,
  availableTools = [],
  currentToolId,
  onChainToTool,
}) => {
  // Mode: 'original' or 'processed'
  const [activeTrack, setActiveTrack] = useState<'original' | 'processed'>('original')
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isDragOver, setIsDragOver] = useState(false)
  const [chainTarget, setChainTarget] = useState('')

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const [waveformPeaks, setWaveformPeaks] = useState<number[]>([])

  // Determine current active URL
  const currentAudioUrl =
    activeTrack === 'processed' && outputAudioUrl ? outputAudioUrl : inputAudioUrl

  // Auto switch to 'processed' when output becomes available
  useEffect(() => {
    if (outputAudioUrl) {
      setActiveTrack('processed')
    }
  }, [outputAudioUrl])

  // Decode audio data for visual waveform
  useEffect(() => {
    if (!currentAudioUrl) {
      setWaveformPeaks([])
      return
    }

    let isMounted = true

    const loadWaveform = async () => {
      try {
        const response = await fetch(currentAudioUrl)
        const arrayBuffer = await response.arrayBuffer()
        
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
        if (!audioContextRef.current) {
          audioContextRef.current = new AudioCtx()
        }

        const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
        if (!isMounted) return

        const channelData = audioBuffer.getChannelData(0)
        const samples = 120 // Number of bars in waveform
        const blockSize = Math.floor(channelData.length / samples)
        const peaks: number[] = []

        for (let i = 0; i < samples; i++) {
          const start = i * blockSize
          let max = 0
          for (let j = 0; j < blockSize; j += 4) {
            const val = Math.abs(channelData[start + j] || 0)
            if (val > max) max = val
          }
          peaks.push(max)
        }

        // Normalize
        const peakMax = Math.max(...peaks, 0.01)
        const normalized = peaks.map((p) => Math.min(1, p / peakMax))
        setWaveformPeaks(normalized)
      } catch {
        // Fallback procedural peaks if decode fails or CORS restricted
        const fallback = Array.from({ length: 120 }, (_, i) => {
          return 0.2 + 0.6 * Math.abs(Math.sin(i * 0.15)) * Math.abs(Math.cos(i * 0.05))
        })
        if (isMounted) setWaveformPeaks(fallback)
      }
    }

    loadWaveform()

    return () => {
      isMounted = false
    }
  }, [currentAudioUrl])

  // Draw canvas waveform
  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    ctx.clearRect(0, 0, width, height)

    const peaks = waveformPeaks.length > 0 ? waveformPeaks : Array.from({ length: 80 }, () => 0.1)
    const barCount = peaks.length
    const gap = 2
    const totalGap = gap * (barCount - 1)
    const barWidth = Math.max(2, (width - totalGap) / barCount)

    const playbackProgress = duration > 0 ? currentTime / duration : 0

    peaks.forEach((peak, i) => {
      const x = i * (barWidth + gap)
      const barHeight = Math.max(4, peak * (height - 8))
      const y = (height - barHeight) / 2

      const isPlayed = i / barCount <= playbackProgress

      // Color coding based on played state & track
      if (activeTrack === 'processed') {
        ctx.fillStyle = isPlayed ? '#10b981' : '#10b98133'
      } else {
        ctx.fillStyle = isPlayed ? '#6366f1' : '#6366f140'
      }

      ctx.beginPath()
      if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(x, y, barWidth, barHeight, 2)
      } else {
        ctx.rect(x, y, barWidth, barHeight)
      }
      ctx.fill()
    })
  }, [waveformPeaks, currentTime, duration, activeTrack])

  useEffect(() => {
    drawWaveform()
  }, [drawWaveform])

  // Audio element listeners
  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
  }

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      const dur = audioRef.current.duration
      setDuration(dur)
      if (isTrimMode && onTrimChange && (endTime === 0 || endTime > dur)) {
        onTrimChange(startTime, dur)
      }
    }
  }

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || duration <= 0) return
    const rect = e.currentTarget.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const pct = Math.max(0, Math.min(1, clickX / rect.width))
    audioRef.current.currentTime = pct * duration
  }

  // Format time (mm:ss.s)
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    const ms = Math.floor((secs % 1) * 10)
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`
  }

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      if (file.type.startsWith('audio/') || /\.(mp3|wav|ogg|flac|m4a|aac)$/i.test(file.name)) {
        onFileSelect(file)
      }
    }
  }

  const otherTools = availableTools.filter((t) => t.id !== currentToolId)

  return (
    <div className="space-y-4">
      {/* 1. Upload Dropzone / Active File Header */}
      {!inputAudioUrl ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-500/10'
              : 'border-slate-200 dark:border-white/10 hover:border-indigo-400 dark:hover:border-indigo-500 bg-slate-50/50 dark:bg-[#12151C]/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac,.aac"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                onFileSelect(e.target.files[0])
              }
            }}
          />
          <div className="w-12 h-12 mx-auto rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-3">
            <Upload className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-semibold text-slate-800 dark:text-white">
            Kéo thả tệp âm thanh vào đây hoặc bấm để chọn tệp
          </h4>
          <p className="text-xs text-slate-500 dark:text-white/40 mt-1">
            Hỗ trợ MP3, WAV, M4A, FLAC, OGG, AAC (tối đa 50MB)
          </p>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0">
              <FileAudio className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-slate-800 dark:text-white truncate">
                {inputFileName || 'Tệp âm thanh'}
              </div>
              <div className="text-[11px] text-slate-400 dark:text-white/40">
                Thời lượng: {formatTime(duration)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-xs px-2.5 py-1.5 rounded-control border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/[0.06] text-slate-700 dark:text-white/80 transition-colors flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Đổi tệp</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac,.aac"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  onFileSelect(e.target.files[0])
                }
              }}
            />
          </div>
        </div>
      )}

      {/* 2. Waveform & Audio Player Player */}
      {currentAudioUrl && (
        <div className="p-4 rounded-2xl bg-white dark:bg-[#0E1117] border border-slate-200 dark:border-white/[0.08] shadow-xs space-y-4">
          {/* Header A/B Toggle if output is available */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-700 dark:text-white/80">
                Chế độ nghe:
              </span>
              <div className="inline-flex rounded-lg p-0.5 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTrack('original')
                    setIsPlaying(false)
                  }}
                  className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                    activeTrack === 'original'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Bản gốc
                </button>
                <button
                  type="button"
                  disabled={!outputAudioUrl}
                  onClick={() => {
                    setActiveTrack('processed')
                    setIsPlaying(false)
                  }}
                  className={`px-2.5 py-1 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                    !outputAudioUrl
                      ? 'opacity-40 cursor-not-allowed text-slate-400'
                      : activeTrack === 'processed'
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Bản xử lý (A/B)</span>
                </button>
              </div>
            </div>

            {outputAudioUrl && activeTrack === 'processed' && (
              <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Đang nghe bản xuất
              </span>
            )}
          </div>

          {/* Interactive Waveform Canvas */}
          <div
            onClick={handleSeek}
            className="relative h-24 bg-slate-50 dark:bg-[#12151C] rounded-xl overflow-hidden cursor-pointer group border border-slate-200/60 dark:border-white/5 flex items-center"
          >
            <canvas
              ref={canvasRef}
              width={600}
              height={96}
              className="w-full h-full block"
            />

            {/* Trim overlay if active */}
            {isTrimMode && duration > 0 && (
              <div
                className="absolute inset-y-0 bg-indigo-500/20 border-x-2 border-indigo-500 pointer-events-none transition-all"
                style={{
                  left: `${(startTime / duration) * 100}%`,
                  width: `${Math.max(0, ((endTime - startTime) / duration) * 100)}%`,
                }}
              />
            )}

            {/* Playhead */}
            {duration > 0 && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 pointer-events-none transition-all"
                style={{ left: `${(currentTime / duration) * 100}%` }}
              />
            )}
          </div>

          {/* Player controls */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={togglePlay}
                disabled={isProcessing}
                className="w-10 h-10 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center transition-transform active:scale-95 disabled:opacity-50"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>
              <div className="font-mono text-xs text-slate-600 dark:text-white/70">
                {formatTime(currentTime)} / {formatTime(duration)}
              </div>
            </div>

            <audio
              ref={audioRef}
              src={currentAudioUrl}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
            />

            {/* Trim Region Controls if tool is trim */}
            {isTrimMode && onTrimChange && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">Đoạn chọn:</span>
                <input
                  type="number"
                  min={0}
                  max={duration}
                  step={0.1}
                  value={startTime}
                  onChange={(e) => onTrimChange(parseFloat(e.target.value) || 0, endTime)}
                  className="w-16 px-1.5 py-1 bg-slate-100 dark:bg-white/10 rounded border border-slate-300 dark:border-white/10 text-xs font-mono"
                />
                <span className="text-slate-400">đến</span>
                <input
                  type="number"
                  min={startTime}
                  max={duration}
                  step={0.1}
                  value={endTime}
                  onChange={(e) => onTrimChange(startTime, parseFloat(e.target.value) || duration)}
                  className="w-16 px-1.5 py-1 bg-slate-100 dark:bg-white/10 rounded border border-slate-300 dark:border-white/10 text-xs font-mono"
                />
                <span className="text-slate-400">giây</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. Progress State */}
      {isProcessing && (
        <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/40 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-indigo-700 dark:text-indigo-300 flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600 dark:text-indigo-400" />
              Đang xử lý âm thanh...
            </span>
            <span className="font-bold text-indigo-600 dark:text-indigo-400 font-mono">
              {progress}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-indigo-200 dark:bg-indigo-900/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-600 dark:bg-indigo-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>
        </div>
      )}

      {/* 4. Chain to another tool (Gửi sang công cụ khác) */}
      {outputAudioUrl && otherTools.length > 0 && onChainToTool && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-purple-500/5 via-indigo-500/5 to-transparent border border-purple-200/50 dark:border-purple-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center flex-shrink-0">
              <Volume2 className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-800 dark:text-white">
                Chuyển tiếp kết quả sang công cụ khác
              </div>
              <div className="text-[11px] text-slate-500 dark:text-white/40">
                Tiếp tục chỉnh sửa tệp đã xử lý với một công cụ khác mà không cần tải lại
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={chainTarget}
              onChange={(e) => setChainTarget(e.target.value)}
              className="bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/10 rounded-control px-2.5 py-1.5 text-xs text-slate-800 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">Chọn công cụ...</option>
              {otherTools.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name_vi}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!chainTarget}
              onClick={() => {
                if (chainTarget) {
                  onChainToTool(chainTarget)
                }
              }}
              className="px-3 py-1.5 rounded-control bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>Chuyển</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
