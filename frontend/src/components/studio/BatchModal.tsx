import { useState, useRef } from 'react'
import JSZip from 'jszip'
import {
  X,
  Upload,
  FileText,
  Trash2,
  Play,
  Download,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Archive,
  Layers,
} from 'lucide-react'
import { createTTSJob, getTTSJob, getJobAudioUrl } from '../../api/tts'
import { useAuth } from '../../hooks/useAuth'

interface BatchItem {
  id: string
  fileName: string
  text: string
  charCount: number
  status: 'ready' | 'queued' | 'processing' | 'done' | 'failed'
  progress: number
  jobId?: number
  audioUrl?: string
  error?: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  defaultVoice: string
  defaultRate: string
  defaultPitch: string
  defaultVolume: string
  selectedFormat: 'mp3' | 'wav'
  applyDictionary: boolean
}

// Hàm trích xuất text từ file SRT (bỏ index số và timestamp)
function parseSrtText(raw: string): string {
  const lines = raw.split(/\r?\n/)
  const textLines: string[] = []
  const timeRegex = /^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}/

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (/^\d+$/.test(trimmed)) continue
    if (timeRegex.test(trimmed)) continue
    textLines.push(trimmed)
  }
  return textLines.join('\n')
}

// Hàm trích xuất text từ file DOCX bằng JSZip
async function parseDocxText(file: File): Promise<string> {
  const zip = new JSZip()
  const content = await zip.loadAsync(file)
  const docXml = await content.file('word/document.xml')?.async('text')
  if (!docXml) return ''

  // Trích xuất tất cả các đoạn <w:p> và <w:t>
  const parser = new DOMParser()
  const xmlDoc = parser.parseFromString(docXml, 'application/xml')
  const paragraphs = xmlDoc.getElementsByTagName('w:p')
  const textParts: string[] = []

  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    const texts = p.getElementsByTagName('w:t')
    let pText = ''
    for (let j = 0; j < texts.length; j++) {
      pText += texts[j].textContent || ''
    }
    if (pText.trim()) {
      textParts.push(pText.trim())
    }
  }

  return textParts.join('\n\n')
}

export default function BatchModal({
  isOpen,
  onClose,
  defaultVoice,
  defaultRate,
  defaultPitch,
  defaultVolume,
  selectedFormat,
  applyDictionary,
}: Props) {
  const { user, refreshUser } = useAuth()
  const [items, setItems] = useState<BatchItem[]>([])
  const [isProcessingAll, setIsProcessingAll] = useState(false)
  const [isZipping, setIsZipping] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!isOpen) return null

  // Xử lý nạp file
  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const newItems: BatchItem[] = []
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const ext = file.name.split('.').pop()?.toLowerCase()
      let extractedText = ''

      try {
        if (ext === 'txt') {
          extractedText = await file.text()
        } else if (ext === 'srt') {
          const raw = await file.text()
          extractedText = parseSrtText(raw)
        } else if (ext === 'docx') {
          extractedText = await parseDocxText(file)
        } else {
          continue
        }
      } catch (err) {
        console.error(`Không thể đọc file ${file.name}:`, err)
        continue
      }

      if (extractedText.trim()) {
        newItems.push({
          id: `${file.name}-${Date.now()}-${Math.random()}`,
          fileName: file.name,
          text: extractedText.trim(),
          charCount: extractedText.trim().length,
          status: 'ready',
          progress: 0,
        })
      }
    }

    setItems((prev) => [...prev, ...newItems])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }

  const handleClearAll = () => {
    setItems([])
  }

  // Tổng credit cần dùng
  const totalChars = items.reduce((sum, item) => sum + item.charCount, 0)
  const userBalance = user?.credits ?? 0
  const isInsufficient = totalChars > userBalance

  // Xử lý tạo từng item lần lượt
  const handleBatchGenerate = async () => {
    if (items.length === 0 || isProcessingAll) return
    setIsProcessingAll(true)

    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.status === 'done') continue

      // Cập nhật trạng thái đang xử lý
      setItems((prev) =>
        prev.map((it) => (it.id === item.id ? { ...it, status: 'processing', progress: 10 } : it))
      )

      try {
        // Tạo async job
        const job = await createTTSJob({
          text: item.text,
          voice: defaultVoice,
          rate: defaultRate,
          pitch: defaultPitch,
          volume: defaultVolume,
          format: selectedFormat,
          apply_dictionary: applyDictionary,
        })

        // Poll job status
        let isDone = false
        let currentJob = job

        while (!isDone) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          currentJob = await getTTSJob(job.id)

          setItems((prev) =>
            prev.map((it) =>
              it.id === item.id
                ? {
                    ...it,
                    jobId: currentJob.id,
                    progress: currentJob.progress,
                    status: currentJob.status,
                    error: currentJob.error_message ?? undefined,
                  }
                : it
            )
          )

          if (currentJob.status === 'done') {
            isDone = true
            setItems((prev) =>
              prev.map((it) =>
                it.id === item.id
                  ? {
                      ...it,
                      status: 'done',
                      progress: 100,
                      audioUrl: getJobAudioUrl(currentJob.id),
                    }
                  : it
              )
            )
          } else if (currentJob.status === 'failed') {
            isDone = true
            setItems((prev) =>
              prev.map((it) =>
                it.id === item.id
                  ? {
                      ...it,
                      status: 'failed',
                      error: currentJob.error_message || 'Xử lý thất bại',
                    }
                  : it
              )
            )
          }
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Lỗi khởi tạo'
        setItems((prev) =>
          prev.map((it) =>
            it.id === item.id ? { ...it, status: 'failed', error: errorMsg } : it
          )
        )
      }
    }

    setIsProcessingAll(false)
    refreshUser()
  }

  // Tải trọn bộ file nén .ZIP
  const handleDownloadZip = async () => {
    const doneItems = items.filter((item) => item.status === 'done' && item.audioUrl)
    if (doneItems.length === 0) return

    setIsZipping(true)
    try {
      const zip = new JSZip()
      for (const item of doneItems) {
        if (!item.audioUrl) continue
        const response = await fetch(item.audioUrl)
        const blob = await response.blob()
        const baseName = item.fileName.substring(0, item.fileName.lastIndexOf('.')) || item.fileName
        zip.file(`${baseName}.${selectedFormat}`, blob)
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(zipBlob)
      link.download = `voxify_batch_${Date.now()}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Lỗi khi nén file zip:', err)
    } finally {
      setIsZipping(false)
    }
  }

  const doneCount = items.filter((i) => i.status === 'done').length

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-3xl bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-card shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-50/70 dark:bg-[#0B0D12]/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                Tạo giọng nói hàng loạt (Batch TTS)
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-white/40">
                Tải lên nhiều file văn bản (.txt, .docx, .srt) để tạo thành audio độc lập
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-control text-slate-400 hover:text-slate-700 dark:text-white/40 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-5 flex-1 scrollbar-thin">
          {/* Upload Area */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              handleFiles(e.dataTransfer.files)
            }}
            className="border-2 border-dashed border-slate-200 dark:border-white/[0.1] hover:border-indigo-500/50 rounded-card p-6 flex flex-col items-center justify-center gap-2 bg-slate-50/50 dark:bg-[#181C25]/40 cursor-pointer transition-all group"
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.docx,.srt"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <div className="w-10 h-10 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Upload className="w-5 h-5" />
            </div>
            <p className="text-xs font-semibold text-slate-800 dark:text-white text-center">
              Kéo thả file vào đây hoặc <span className="text-indigo-600 dark:text-indigo-400">bấm để chọn</span>
            </p>
            <p className="text-[11px] text-slate-500 dark:text-white/40">
              Hỗ trợ file văn bản <span className="font-mono font-medium">.txt</span>, tài liệu{' '}
              <span className="font-mono font-medium">.docx</span>, phụ đề{' '}
              <span className="font-mono font-medium">.srt</span>
            </p>
          </div>

          {/* Files List */}
          {items.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-800 dark:text-white uppercase tracking-wider">
                  Danh sách file ({items.length})
                </span>
                <button
                  onClick={handleClearAll}
                  disabled={isProcessingAll}
                  className="text-[11px] text-rose-500 hover:text-rose-600 font-medium disabled:opacity-50"
                >
                  Xóa tất cả
                </button>
              </div>

              <div className="border border-slate-200 dark:border-white/[0.08] rounded-control overflow-hidden divide-y divide-slate-100 dark:divide-white/[0.04]">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 bg-white dark:bg-[#181C25]/60 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-slate-400 dark:text-white/40 shrink-0" />
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900 dark:text-white truncate">
                          {item.fileName}
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-white/40 font-mono">
                          {item.charCount.toLocaleString('vi-VN')} ký tự &middot; ~
                          {item.charCount.toLocaleString('vi-VN')} credit
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {/* Trạng thái */}
                      {item.status === 'ready' && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-white/60 font-medium">
                          Sẵn sàng
                        </span>
                      )}
                      {item.status === 'processing' && (
                        <div className="flex items-center gap-1.5 text-[10px] text-indigo-600 dark:text-indigo-400 font-mono">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>{item.progress}%</span>
                        </div>
                      )}
                      {item.status === 'done' && (
                        <div className="flex items-center gap-1.5">
                          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold">
                            <CheckCircle2 className="w-3 h-3" />
                            Đã tạo
                          </span>
                          {item.audioUrl && (
                            <a
                              href={item.audioUrl}
                              download
                              className="p-1 rounded text-slate-500 hover:text-slate-900 dark:text-white/50 dark:hover:text-white"
                              title="Tải audio"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      )}
                      {item.status === 'failed' && (
                        <span
                          className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 font-bold"
                          title={item.error}
                        >
                          <AlertCircle className="w-3 h-3" />
                          Lỗi
                        </span>
                      )}

                      {/* Xóa item */}
                      <button
                        onClick={() => handleRemoveItem(item.id)}
                        disabled={isProcessingAll && item.status === 'processing'}
                        className="p-1 text-slate-400 hover:text-rose-600 dark:text-white/30 dark:hover:text-rose-400 disabled:opacity-40"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 sm:p-5 border-t border-slate-200 dark:border-white/[0.08] bg-slate-50/70 dark:bg-[#0B0D12]/70 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs">
            <span className="text-slate-500 dark:text-white/40">Tổng ước tính: </span>
            <span className="font-mono font-bold text-[#F59E0B]">
              ~{totalChars.toLocaleString('vi-VN')} credit
            </span>
            {isInsufficient && (
              <span className="text-rose-500 ml-2 font-medium">
                (Số dư không đủ: {userBalance.toLocaleString('vi-VN')})
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {doneCount > 0 && (
              <button
                type="button"
                onClick={handleDownloadZip}
                disabled={isZipping}
                className="flex items-center gap-1.5 px-3 py-2 rounded-control bg-white dark:bg-[#181C25] hover:bg-slate-50 dark:hover:bg-[#202532] border border-slate-200 dark:border-white/[0.1] text-xs font-semibold text-slate-800 dark:text-white shadow-xs"
              >
                {isZipping ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Archive className="w-3.5 h-3.5 text-indigo-500" />
                )}
                <span>Tải .ZIP ({doneCount})</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleBatchGenerate}
              disabled={items.length === 0 || isProcessingAll || isInsufficient}
              className="flex items-center gap-2 px-5 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-lg shadow-indigo-600/20 transition-all"
            >
              {isProcessingAll ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang xử lý hàng loạt...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Tạo tất cả ({items.length})</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
