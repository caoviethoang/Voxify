import React, { useState, useRef } from 'react'
import { Play, Square, AlertTriangle, Zap, Clock } from 'lucide-react'
import { SubtitleCueItem, dubbingApi } from '../../api/dubbing'
import { Voice } from '../../api/tts'

interface CueTableProps {
  cues: SubtitleCueItem[]
  voices: Voice[]
  defaultVoice: string
  onUpdateCue: (index: number, updated: Partial<SubtitleCueItem>) => void
}

export const CueTable: React.FC<CueTableProps> = ({
  cues,
  voices,
  defaultVoice,
  onUpdateCue,
}) => {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null)
  const [loadingIndex, setLoadingIndex] = useState<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handlePreview = async (cue: SubtitleCueItem) => {
    if (playingIndex === cue.index) {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      setPlayingIndex(null)
      return
    }

    try {
      setLoadingIndex(cue.index)
      const res = await dubbingApi.previewCue(
        cue.text,
        cue.voice || defaultVoice,
        cue.duration
      )

      onUpdateCue(cue.index, {
        actual_duration: res.actualDuration,
        adjusted_tempo: res.adjustedTempo,
        warning: res.warning,
      })

      const audioUrl = URL.createObjectURL(res.audioBlob)
      const audio = new Audio(audioUrl)
      audioRef.current = audio

      audio.onended = () => {
        setPlayingIndex(null)
        URL.revokeObjectURL(audioUrl)
      }

      audio.onerror = () => {
        setPlayingIndex(null)
        URL.revokeObjectURL(audioUrl)
      }

      await audio.play()
      setPlayingIndex(cue.index)
    } catch (err) {
      console.error('Lỗi nghe thử cue:', err)
    } finally {
      setLoadingIndex(null)
    }
  }

  const formatTimestamp = (sec: number) => {
    const mins = Math.floor(sec / 60)
    const secs = Math.floor(sec % 60)
    const ms = Math.floor((sec - Math.floor(sec)) * 10)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms}`
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] shadow-xs">
      <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
        <thead className="bg-slate-50 dark:bg-[#181B24] border-b border-slate-200 dark:border-white/[0.08] text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
          <tr>
            <th className="py-3 px-3 w-12 text-center">#</th>
            <th className="py-3 px-3 w-36">Thời gian</th>
            <th className="py-3 px-4">Nội dung phụ đề</th>
            <th className="py-3 px-3 w-48">Giọng đọc</th>
            <th className="py-3 px-3 w-40 text-center">Khớp thời gian</th>
            <th className="py-3 px-3 w-28 text-center">Nghe thử</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-white/[0.05]">
          {cues.map((cue) => {
            const hasWarning = Boolean(cue.warning || (cue.adjusted_tempo && cue.adjusted_tempo > 1.35))
            const hasTempo = Boolean(cue.adjusted_tempo && cue.adjusted_tempo > 1.0)
            const isPlaying = playingIndex === cue.index
            const isLoading = loadingIndex === cue.index

            return (
              <tr
                key={cue.index}
                className={`transition-colors hover:bg-slate-50/80 dark:hover:bg-white/[0.02] ${
                  hasWarning ? 'bg-amber-500/[0.03]' : ''
                }`}
              >
                {/* Index */}
                <td className="py-3 px-3 text-center font-mono font-bold text-slate-400 dark:text-slate-500">
                  {cue.index}
                </td>

                {/* Timestamp */}
                <td className="py-3 px-3 font-mono">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-slate-900 dark:text-white font-medium">
                      {formatTimestamp(cue.start)} ➔ {formatTimestamp(cue.end)}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400">
                      <Clock className="w-3 h-3 text-indigo-500" />
                      {cue.duration.toFixed(1)}s cho phép
                    </span>
                  </div>
                </td>

                {/* Subtitle Text (Editable) */}
                <td className="py-2.5 px-4">
                  <textarea
                    rows={2}
                    value={cue.text}
                    onChange={(e) => {
                      const newText = e.target.value
                      onUpdateCue(cue.index, {
                        text: newText,
                        char_count: newText.length,
                        actual_duration: undefined,
                        adjusted_tempo: undefined,
                        warning: undefined,
                      })
                    }}
                    className="w-full resize-none rounded-lg border border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-[#0B0D12] p-2 text-xs leading-relaxed text-slate-800 dark:text-slate-200 focus:border-indigo-500 focus:bg-white dark:focus:bg-[#12151C] focus:outline-hidden transition-all"
                  />
                  <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400">
                    <span>{cue.char_count} ký tự</span>
                    {cue.original_voice_tag && (
                      <span className="text-purple-600 dark:text-purple-400 font-mono">
                        Tag: [{cue.original_voice_tag}]
                      </span>
                    )}
                  </div>
                </td>

                {/* Voice Selection */}
                <td className="py-3 px-3">
                  <select
                    value={cue.voice || defaultVoice}
                    onChange={(e) => onUpdateCue(cue.index, { voice: e.target.value })}
                    className="w-full rounded-lg border border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#0B0D12] py-1.5 px-2.5 text-xs text-slate-800 dark:text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.gender === 'female' ? 'Nữ' : 'Nam'})
                      </option>
                    ))}
                  </select>
                </td>

                {/* Time Sync / Tempo status */}
                <td className="py-3 px-3 text-center">
                  <div className="flex flex-col items-center justify-center gap-1">
                    {cue.actual_duration ? (
                      <span className="text-[11px] font-mono text-slate-600 dark:text-slate-300">
                        Thực tế: {cue.actual_duration.toFixed(1)}s
                      </span>
                    ) : (
                      <span className="text-[11px] text-slate-400 italic">Chưa kiểm tra</span>
                    )}

                    {hasWarning && (
                      <div
                        className="flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-400"
                        title={cue.warning || 'Vượt quá thời lượng an toàn!'}
                      >
                        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                        <span>Vượt ngưỡng (+{((cue.actual_duration || 0) - cue.duration).toFixed(1)}s)</span>
                      </div>
                    )}

                    {!hasWarning && hasTempo && (
                      <div className="flex items-center gap-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                        <Zap className="w-3 h-3 flex-shrink-0" />
                        <span>Co dãn {cue.adjusted_tempo}x</span>
                      </div>
                    )}
                  </div>
                </td>

                {/* Actions */}
                <td className="py-3 px-3 text-center">
                  <button
                    type="button"
                    onClick={() => handlePreview(cue)}
                    disabled={isLoading}
                    className={`inline-flex items-center justify-center w-8 h-8 rounded-full transition-all ${
                      isPlaying
                        ? 'bg-rose-500 text-white shadow-xs'
                        : 'bg-indigo-50 hover:bg-indigo-100 text-indigo-600 dark:bg-indigo-500/10 dark:hover:bg-indigo-500/20 dark:text-indigo-400'
                    }`}
                    title={isPlaying ? 'Dừng phát' : 'Nghe thử câu này'}
                  >
                    {isLoading ? (
                      <div className="w-3.5 h-3.5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    ) : isPlaying ? (
                      <Square className="w-3.5 h-3.5 fill-current" />
                    ) : (
                      <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                    )}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
