import React, { useState } from 'react'
import { Music, Upload, CheckCircle2, Sliders, VolumeX } from 'lucide-react'
import { dubbingApi } from '../../api/dubbing'

interface DuckingSettingsProps {
  enabled: boolean
  onToggle: (enabled: boolean) => void
  duckingVolume: number
  onChangeVolume: (vol: number) => void
  backgroundAudioPath: string | null
  onSetBackgroundPath: (path: string | null) => void
}

export const DuckingSettings: React.FC<DuckingSettingsProps> = ({
  enabled,
  onToggle,
  duckingVolume,
  onChangeVolume,
  backgroundAudioPath,
  onSetBackgroundPath,
}) => {
  const [uploading, setUploading] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setUploading(true)
      const res = await dubbingApi.uploadBackgroundMusic(file)
      onSetBackgroundPath(res.background_audio_path)
      setFileName(res.filename)
    } catch (err) {
      console.error('Lỗi tải file nhạc nền:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] p-4 shadow-xs space-y-4">
      {/* Header with Switch */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center flex-shrink-0">
            <Music className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-900 dark:text-white">
              Hòa âm nền thông minh (Audio Ducking)
            </h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Tự động giảm âm lượng nhạc nền khi có câu thoại phát ra
            </p>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-slate-200 peer-focus:outline-hidden rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-slate-600 peer-checked:bg-indigo-600" />
        </label>
      </div>

      {/* Expanded settings when enabled */}
      {enabled && (
        <div className="pt-3 border-t border-slate-100 dark:border-white/[0.05] grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* File Upload */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Upload className="w-3.5 h-3.5 text-indigo-500" />
              Chọn tệp nhạc nền (MP3, WAV):
            </label>
            <div className="flex items-center gap-2">
              <label className="flex-1 cursor-pointer flex items-center justify-center gap-2 border-2 border-dashed border-slate-200 dark:border-white/[0.1] hover:border-indigo-400 rounded-lg p-2.5 text-xs text-slate-600 dark:text-slate-300 transition-colors bg-slate-50/50 dark:bg-[#0B0D12]">
                <input
                  type="file"
                  accept="audio/mp3,audio/wav,audio/m4a,audio/aac,audio/ogg"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={uploading}
                />
                {uploading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-3.5 h-3.5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span>Đang tải lên...</span>
                  </div>
                ) : backgroundAudioPath ? (
                  <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium truncate">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{fileName || 'Đã nạp nhạc nền'}</span>
                  </div>
                ) : (
                  <span>Tải lên tệp nhạc nền</span>
                )}
              </label>

              {backgroundAudioPath && (
                <button
                  type="button"
                  onClick={() => {
                    onSetBackgroundPath(null)
                    setFileName(null)
                  }}
                  className="p-2.5 text-slate-400 hover:text-rose-500 rounded-lg border border-slate-200 dark:border-white/[0.08]"
                  title="Hủy chọn nhạc nền"
                >
                  <VolumeX className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Ducking Volume Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-medium text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-purple-500" />
                Mức âm lượng nhạc nền khi có lời nói:
              </span>
              <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                {Math.round(duckingVolume * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.5"
              step="0.05"
              value={duckingVolume}
              onChange={(e) => onChangeVolume(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-[9px] text-slate-400">
              <span>Rất nhỏ (5%)</span>
              <span>Cân bằng (20%)</span>
              <span>Vừa phải (50%)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
