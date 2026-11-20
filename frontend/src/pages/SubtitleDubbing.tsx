import React, { useState, useEffect } from 'react'
import {
  Upload,
  FileText,
  Sparkles,
  Play,
  Film,
  Coins,
  AlertCircle,
  FileCode,
} from 'lucide-react'
import { useVoices } from '../hooks/useVoices'
import { useCredit } from '../hooks/useCredit'
import {
  SubtitleCueItem,
  DubbingJob,
  dubbingApi,
} from '../api/dubbing'
import { CueTable } from '../components/dubbing/CueTable'
import { DuckingSettings } from '../components/dubbing/DuckingSettings'
import { DubbingJobResult } from '../components/dubbing/DubbingJobResult'
import { extractApiErrorMessage } from '../utils/apiError'

const DEFAULT_SAMPLE_SRT = `1
00:00:01,000 --> 00:00:03,500
[Voice: vi-VN-NamMinhNeural] Chào mừng bạn đến với Studio lồng tiếng phụ đề video Voxify.

2
00:00:04,000 --> 00:00:07,000
Hệ thống tự động đồng bộ giọng nói khớp thời gian theo từng giây với sai số cực nhỏ.

3
00:00:07,500 --> 00:00:10,500
Tự động tăng tốc độ đọc mượt mà và hỗ trợ hòa âm nhạc nền thông minh.
`

export default function SubtitleDubbing() {
  const { data: voiceData } = useVoices()
  const { balance, refreshCredits } = useCredit()

  const [inputMode, setInputMode] = useState<'upload' | 'text'>('upload')
  const [rawText, setRawText] = useState(DEFAULT_SAMPLE_SRT)
  const [defaultVoice, setDefaultVoice] = useState('vi-VN-HoaiMyNeural')
  const [cues, setCues] = useState<SubtitleCueItem[]>([])
  const [estimatedCredits, setEstimatedCredits] = useState(0)
  const [parsing, setParsing] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Ducking Settings
  const [duckingEnabled, setDuckingEnabled] = useState(false)
  const [duckingVolume, setDuckingVolume] = useState(0.2)
  const [backgroundAudioPath, setBackgroundAudioPath] = useState<string | null>(null)

  // Output format
  const [targetFormat, setTargetFormat] = useState<'mp3' | 'wav'>('mp3')

  // Job execution state
  const [activeJob, setActiveJob] = useState<DubbingJob | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const voices = voiceData?.voices || []

  // Phân tích kịch bản mẫu khi mở trang lần đầu
  useEffect(() => {
    if (cues.length === 0 && rawText) {
      handleParseText(rawText)
    }
  }, [])

  // Polling tiến trình khi có activeJob đang chạy
  useEffect(() => {
    if (!activeJob) return
    if (activeJob.status === 'done' || activeJob.status === 'failed') return

    const timer = setInterval(async () => {
      try {
        const updated = await dubbingApi.getJob(activeJob.id)
        setActiveJob(updated)
        if (updated.status === 'done' || updated.status === 'failed') {
          clearInterval(timer)
          refreshCredits()
        }
      } catch (err) {
        console.error('Lỗi kiểm tra tiến trình:', err)
      }
    }, 2000)

    return () => clearInterval(timer)
  }, [activeJob, refreshCredits])

  const handleParseText = async (textToParse: string) => {
    try {
      setParsing(true)
      setErrorMsg(null)
      const res = await dubbingApi.parseSubtitles(textToParse, defaultVoice)
      setCues(res.cues)
      setEstimatedCredits(res.estimated_credits)
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err, 'Không thể phân tích nội dung phụ đề.'))
    } finally {
      setParsing(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setParsing(true)
      setErrorMsg(null)
      const res = await dubbingApi.uploadSubtitleFile(file, defaultVoice)
      setCues(res.cues)
      setEstimatedCredits(res.estimated_credits)
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err, 'Không thể đọc tệp phụ đề.'))
    } finally {
      setParsing(false)
    }
  }

  const handleUpdateCue = (index: number, updated: Partial<SubtitleCueItem>) => {
    setCues((prev) => {
      const next = prev.map((c) => (c.index === index ? { ...c, ...updated } : c))
      // Cập nhật lại ước tính credit
      const totalChars = next.reduce((sum, item) => sum + item.char_count, 0)
      setEstimatedCredits(totalChars)
      return next
    })
  }

  const handleStartDubbing = async () => {
    if (cues.length === 0) {
      setErrorMsg('Vui lòng tải lên hoặc dán nội dung phụ đề trước.')
      return
    }

    const currentBalance = balance ?? 10000
    if (currentBalance < estimatedCredits) {
      setErrorMsg(`Số dư credit không đủ (${currentBalance} < ${estimatedCredits}). Vui lòng nạp thêm.`)
      return
    }

    try {
      setIsSubmitting(true)
      setErrorMsg(null)
      const job = await dubbingApi.createJob({
        title: `Lồng tiếng (${cues.length} câu)`,
        subtitle_format: 'srt',
        target_format: targetFormat,
        default_voice: defaultVoice,
        cues,
        ducking_volume: duckingEnabled ? duckingVolume : 0.0,
        background_audio_path: duckingEnabled ? backgroundAudioPath : null,
      })
      setActiveJob(job)
      refreshCredits()
    } catch (err) {
      setErrorMsg(extractApiErrorMessage(err, 'Không thể khởi tạo tác vụ lồng tiếng.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setActiveJob(null)
    setErrorMsg(null)
  }

  const totalChars = cues.reduce((sum, c) => sum + c.char_count, 0)
  const warningsCount = cues.filter(
    (c) => Boolean(c.warning || (c.adjusted_tempo && c.adjusted_tempo > 1.35))
  ).length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* 1. Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
              <Film className="w-5 h-5" />
            </span>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              Lồng tiếng phụ đề (SRT / VTT → Audio Khớp Thời Gian)
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Chuyển phụ đề video thành giọng nói tự nhiên, tự động co dãn tempo để khớp từng mili-giây và xuất gói file tiện dụng.
          </p>
        </div>

        {/* Credit Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] px-3.5 py-2 rounded-xl">
          <Coins className="w-4 h-4 text-amber-500" />
          <div className="text-xs">
            <span className="text-slate-500 dark:text-slate-400">Số dư: </span>
            <span className="font-bold font-mono text-slate-800 dark:text-white">
              {(balance ?? 10000).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Active Job Result Banner */}
      {activeJob && (
        <DubbingJobResult job={activeJob} onReset={handleReset} />
      )}

      {/* 3. Error Banner */}
      {errorMsg && (
        <div className="flex items-center gap-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 p-3.5 text-xs font-medium text-rose-600 dark:text-rose-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 4. Subtitle Source Input Panel */}
      <div className="rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] p-4 sm:p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Mode Switcher */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-[#181B24] rounded-lg self-start">
            <button
              type="button"
              onClick={() => setInputMode('upload')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                inputMode === 'upload'
                  ? 'bg-white dark:bg-[#0B0D12] text-slate-900 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              Tải lên tệp (.srt / .vtt)
            </button>
            <button
              type="button"
              onClick={() => setInputMode('text')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                inputMode === 'text'
                  ? 'bg-white dark:bg-[#0B0D12] text-slate-900 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              Dán nội dung phụ đề
            </button>
          </div>

          {/* Default Voice Picker */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">Giọng đọc mặc định:</span>
            <select
              value={defaultVoice}
              onChange={(e) => {
                const newV = e.target.value
                setDefaultVoice(newV)
                // Cập nhật cho các cue chưa có tag riêng
                setCues((prev) =>
                  prev.map((c) => (c.original_voice_tag ? c : { ...c, voice: newV }))
                )
              }}
              className="rounded-lg border border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-[#0B0D12] py-1.5 px-2.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-hidden"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Upload Mode */}
        {inputMode === 'upload' && (
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 dark:border-white/[0.1] hover:border-indigo-400 rounded-xl p-6 cursor-pointer bg-slate-50/50 dark:bg-[#0B0D12]/50 transition-colors">
            <input
              type="file"
              accept=".srt,.vtt,text/plain"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Upload className="w-8 h-8 text-indigo-500 mb-2" />
            <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
              Nhấp để chọn hoặc kéo thả tệp SRT / VTT vào đây
            </span>
            <span className="text-[11px] text-slate-400 mt-1">
              Hỗ trợ gắn thẻ đa giọng nói dạng <code className="font-mono text-purple-600">[Voice: tên_giọng]</code>
            </span>
          </label>
        )}

        {/* Text Mode */}
        {inputMode === 'text' && (
          <div className="space-y-3">
            <textarea
              rows={6}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Dán nội dung SRT hoặc WebVTT tại đây..."
              className="w-full resize-y rounded-xl border border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-[#0B0D12] p-3 text-xs font-mono text-slate-800 dark:text-slate-200 focus:bg-white dark:focus:bg-[#12151C] focus:outline-hidden"
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => handleParseText(rawText)}
                disabled={parsing}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{parsing ? 'Đang phân tích...' : 'Phân tích các câu phụ đề'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Stats Strip */}
        {cues.length > 0 && (
          <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-slate-100 dark:border-white/[0.05] text-xs">
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
              <FileText className="w-4 h-4 text-indigo-500" />
              <span>
                Tổng số câu: <strong className="text-slate-900 dark:text-white">{cues.length}</strong>
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
              <span>
                Tổng ký tự: <strong className="text-slate-900 dark:text-white">{totalChars}</strong>
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
              <Coins className="w-4 h-4 text-amber-500" />
              <span>
                Ước tính tiêu tốn:{' '}
                <strong className="text-amber-600 dark:text-amber-400 font-mono">
                  {estimatedCredits.toLocaleString()} credit
                </strong>
              </span>
            </div>
            {warningsCount > 0 && (
              <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-medium">
                <span>⚠️ {warningsCount} câu có thể cần rút ngắn</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. Cues Interactive Table */}
      {cues.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Kịch bản câu thoại ({cues.length} câu)
            </h3>
            <span className="text-xs text-slate-400">
              Có thể chỉnh sửa nội dung hoặc thay đổi giọng đọc cho từng câu
            </span>
          </div>

          <CueTable
            cues={cues}
            voices={voices}
            defaultVoice={defaultVoice}
            onUpdateCue={handleUpdateCue}
          />
        </div>
      )}

      {/* 6. Audio Ducking Settings */}
      {cues.length > 0 && (
        <DuckingSettings
          enabled={duckingEnabled}
          onToggle={setDuckingEnabled}
          duckingVolume={duckingVolume}
          onChangeVolume={setDuckingVolume}
          backgroundAudioPath={backgroundAudioPath}
          onSetBackgroundPath={setBackgroundAudioPath}
        />
      )}

      {/* 7. Action Bar */}
      {cues.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] shadow-xs">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 dark:text-slate-400">Định dạng âm thanh:</span>
            <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/[0.08] p-0.5 bg-slate-50 dark:bg-[#0B0D12]">
              <button
                type="button"
                onClick={() => setTargetFormat('mp3')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  targetFormat === 'mp3'
                    ? 'bg-white dark:bg-[#181B24] text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                }`}
              >
                MP3 (Nhẹ & Phổ biến)
              </button>
              <button
                type="button"
                onClick={() => setTargetFormat('wav')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  targetFormat === 'wav'
                    ? 'bg-white dark:bg-[#181B24] text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                }`}
              >
                WAV (Không nén)
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={handleStartDubbing}
            disabled={Boolean(isSubmitting || parsing || (activeJob && (activeJob.status === 'queued' || activeJob.status === 'processing')))}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Đang khởi tạo tác vụ...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Bắt đầu Lồng Tiếng Khớp Thời Gian ({estimatedCredits.toLocaleString()} cr)</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
