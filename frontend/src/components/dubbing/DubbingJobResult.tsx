import React from 'react'
import { Download, FileArchive, CheckCircle2, AlertCircle, RefreshCw, FileAudio } from 'lucide-react'
import { DubbingJob } from '../../api/dubbing'
import AudioPlayer from '../AudioPlayer'

interface DubbingJobResultProps {
  job: DubbingJob | null
  onReset: () => void
}

export const DubbingJobResult: React.FC<DubbingJobResultProps> = ({ job, onReset }) => {
  if (!job) return null

  const isProcessing = job.status === 'queued' || job.status === 'processing'
  const isDone = job.status === 'done'
  const isFailed = job.status === 'failed'

  return (
    <div className="rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-[#12151C] p-5 shadow-sm space-y-4">
      {/* Header status */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/[0.05]">
        <div className="flex items-center gap-2.5">
          {isProcessing && (
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <RefreshCw className="w-4 h-4 animate-spin" />
            </div>
          )}
          {isDone && (
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          )}
          {isFailed && (
            <div className="w-8 h-8 rounded-lg bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center">
              <AlertCircle className="w-4 h-4" />
            </div>
          )}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              {job.title}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isProcessing && `Đang xử lý lồng tiếng (${job.progress}%)...`}
              {isDone && `Hoàn tất • ${job.total_cues} câu • Thời lượng: ${job.duration}s`}
              {isFailed && 'Quá trình tổng hợp thất bại.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="text-xs font-medium text-slate-500 hover:text-slate-800 dark:hover:text-white px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-white/[0.08]"
        >
          Làm mới kịch bản
        </button>
      </div>

      {/* Progress Bar */}
      {isProcessing && (
        <div className="space-y-2 py-2">
          <div className="flex justify-between text-xs font-medium text-slate-600 dark:text-slate-300">
            <span>Tiến độ tổng hợp & khớp thời gian</span>
            <span>{job.progress}%</span>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-600 h-full transition-all duration-300 rounded-full"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error state */}
      {isFailed && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-xs text-rose-600 dark:text-rose-400">
          <strong>Lỗi:</strong> {job.error_message || 'Có lỗi xảy ra trong quá trình lồng tiếng.'}
        </div>
      )}

      {/* Completed State */}
      {isDone && (
        <div className="space-y-4 pt-1">
          {/* Audio Player for Master Output */}
          {job.audio_download_url && (
            <div className="rounded-lg border border-slate-200/80 dark:border-white/[0.06] overflow-hidden">
              <AudioPlayer
                url={job.audio_download_url}
                voiceName={job.default_voice}
                duration={job.duration}
                format={job.target_format === 'wav' ? 'wav' : 'mp3'}
              />
            </div>
          )}

          {/* Download Actions */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            {job.audio_download_url && (
              <a
                href={job.audio_download_url}
                download={`dubbing_master_${job.id}.${job.target_format}`}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-xs transition-all"
              >
                <FileAudio className="w-4 h-4" />
                <span>Tải Audio Master ({job.target_format.toUpperCase()})</span>
                <Download className="w-3.5 h-3.5 opacity-80" />
              </a>
            )}

            {job.zip_download_url && (
              <a
                href={job.zip_download_url}
                download={`dubbing_cues_${job.id}.zip`}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-white/[0.1] hover:bg-slate-50 dark:hover:bg-white/[0.04] text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all"
              >
                <FileArchive className="w-4 h-4 text-purple-500" />
                <span>Tải gói ZIP (Các câu & Phụ đề)</span>
                <Download className="w-3.5 h-3.5 opacity-80" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
