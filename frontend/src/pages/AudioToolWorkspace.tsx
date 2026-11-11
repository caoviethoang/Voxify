import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAudioTool, useAudioTools, useAudioToolJob } from '../hooks/useAudioTools'
import { createAudioToolJob } from '../api/audio_tools'
import { DynamicParamsForm } from '../components/tools/DynamicParamsForm'
import { AudioWaveformWorkspace } from '../components/tools/AudioWaveformWorkspace'
import { ToolIcon } from '../components/tools/ToolIcon'
import { useToast } from '../hooks/useToast'
import {
  ArrowLeft,
  Play,
  Download,
  AlertCircle,
  Zap,
  Sparkles,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react'

interface LocationState {
  source_tool_job_id?: string
  source_generation_id?: number
  fileName?: string
}

export default function AudioToolWorkspace() {
  const { toolId } = useParams<{ toolId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const toast = useToast()

  const locationState = (location.state as LocationState) || {}

  const { data: tool, isLoading: toolLoading, error: toolError } = useAudioTool(toolId)
  const { data: toolsData } = useAudioTools()

  const allTools = useMemo(() => {
    return toolsData?.categories?.flatMap((c) => c.tools) || []
  }, [toolsData])

  // File and input states
  const [file, setFile] = useState<File | null>(null)
  const [inputUrl, setInputUrl] = useState<string | null>(null)
  const [sourceJobId, setSourceJobId] = useState<string | null>(
    locationState.source_tool_job_id || null
  )
  const [sourceGenId] = useState<number | null>(
    locationState.source_generation_id || null
  )
  const [inputFileName, setInputFileName] = useState<string>(
    locationState.fileName || ''
  )

  // Dynamic parameters state
  const [params, setParams] = useState<Record<string, unknown>>({})

  // Active Job processing
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [outputUrl, setOutputUrl] = useState<string | null>(null)

  const { data: activeJob } = useAudioToolJob(activeJobId)

  // Initialize parameter defaults whenever tool schema changes
  useEffect(() => {
    if (tool?.params_schema?.properties) {
      const defaults: Record<string, unknown> = {}
      Object.entries(tool.params_schema.properties).forEach(([key, prop]) => {
        if (prop.default !== undefined) {
          defaults[key] = prop.default
        }
      })
      setParams(defaults)
    }
  }, [tool])

  // Handle source job ID from navigation or chaining
  useEffect(() => {
    if (sourceJobId) {
      setInputUrl(`/api/tools/jobs/${sourceJobId}/stream`)
      if (!inputFileName) {
        setInputFileName(`job-${sourceJobId.slice(0, 8)}`)
      }
    }
  }, [sourceJobId, inputFileName])

  // Handle source generation ID if passed
  useEffect(() => {
    if (sourceGenId) {
      setInputUrl(`/api/tts/stream/${sourceGenId}`)
      if (!inputFileName) {
        setInputFileName(`tts-audio-${sourceGenId}`)
      }
    }
  }, [sourceGenId, inputFileName])

  // Handle completed job updates
  useEffect(() => {
    if (activeJob) {
      if (activeJob.status === 'done') {
        setOutputUrl(activeJob.stream_url)
        setIsSubmitting(false)
        queryClient.invalidateQueries({ queryKey: ['credit'] })
        queryClient.invalidateQueries({ queryKey: ['audio-tool-jobs'] })
        toast.success(`Xử lý thành công bằng ${tool?.name_vi || 'công cụ'}!`)
      } else if (activeJob.status === 'failed') {
        setIsSubmitting(false)
        toast.error(activeJob.error_message || 'Xử lý âm thanh thất bại.')
      }
    }
  }, [activeJob, tool, queryClient, toast])

  const handleFileSelect = useCallback((selectedFile: File) => {
    setFile(selectedFile)
    setInputFileName(selectedFile.name)
    setSourceJobId(null)
    setOutputUrl(null)
    setActiveJobId(null)

    // Revoke previous object URL if needed
    if (inputUrl && inputUrl.startsWith('blob:')) {
      URL.revokeObjectURL(inputUrl)
    }
    const newBlobUrl = URL.createObjectURL(selectedFile)
    setInputUrl(newBlobUrl)
  }, [inputUrl])

  const handleParamChange = useCallback((key: string, value: unknown) => {
    setParams((prev) => ({
      ...prev,
      [key]: value,
    }))
  }, [])

  const handleResetParams = useCallback(() => {
    if (tool?.params_schema?.properties) {
      const defaults: Record<string, unknown> = {}
      Object.entries(tool.params_schema.properties).forEach(([key, prop]) => {
        if (prop.default !== undefined) {
          defaults[key] = prop.default
        }
      })
      setParams(defaults)
    }
  }, [tool])

  // Trim sync helper
  const isTrimTool = toolId === 'trim'
  const startTime = typeof params.start_time === 'number' ? params.start_time : 0
  const endTime = typeof params.end_time === 'number' ? params.end_time : 0

  const handleTrimChange = useCallback((start: number, end: number) => {
    setParams((prev) => ({
      ...prev,
      start_time: Math.round(start * 10) / 10,
      end_time: Math.round(end * 10) / 10,
    }))
  }, [])

  // Execute Tool Job
  const handleExecute = async () => {
    if (!toolId) return
    if (!file && !sourceJobId && !sourceGenId) {
      toast.error('Vui lòng tải lên tệp âm thanh hoặc chọn nguồn âm thanh để xử lý.')
      return
    }

    try {
      setIsSubmitting(true)
      setOutputUrl(null)

      const job = await createAudioToolJob(toolId, {
        file,
        source_generation_id: sourceGenId,
        source_tool_job_id: sourceJobId,
        params,
      })

      setActiveJobId(job.id)

      if (job.status === 'done') {
        setOutputUrl(job.stream_url)
        setIsSubmitting(false)
        queryClient.invalidateQueries({ queryKey: ['credit'] })
        queryClient.invalidateQueries({ queryKey: ['audio-tool-jobs'] })
        toast.success(`Xử lý thành công!`)
      }
    } catch (err: unknown) {
      setIsSubmitting(false)
      const errorObj = err as { response?: { data?: { detail?: string } } }
      const msg = errorObj.response?.data?.detail || 'Không thể tạo tác vụ xử lý. Vui lòng kiểm tra lại.'
      toast.error(msg)
    }
  }

  // Chaining to another tool
  const handleChainToTool = (targetToolId: string) => {
    if (!activeJob) return
    navigate(`/tools/${targetToolId}`, {
      state: {
        source_tool_job_id: activeJob.id,
        fileName: activeJob.input_filename || 'output.mp3',
      },
    })
  }

  if (toolLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 flex flex-col items-center justify-center space-y-4">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Đang khởi tạo không gian công cụ...</span>
      </div>
    )
  }

  if (toolError || !tool) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
          Không tìm thấy công cụ âm thanh
        </h2>
        <p className="text-xs text-slate-500 dark:text-white/50">
          Công cụ yêu cầu không tồn tại hoặc đã bị gỡ bỏ.
        </p>
        <Link
          to="/tools"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Về trang công cụ</span>
        </Link>
      </div>
    )
  }

  const isProcessing =
    isSubmitting ||
    activeJob?.status === 'queued' ||
    activeJob?.status === 'processing'
  const progressVal = activeJob?.progress ?? (isSubmitting ? 10 : 0)

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* 1. Header & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-white/[0.08]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/tools')}
            className="p-2 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/[0.06] text-slate-600 dark:text-white/70 transition-colors"
            title="Quay lại danh sách công cụ"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
            <ToolIcon name={tool.icon} className="w-5 h-5" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 dark:text-white">
                {tool.name_vi}
              </h1>
              {tool.cost_type === 'free' ? (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  Miễn phí
                </span>
              ) : (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {tool.cost_credits} cr/phút
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-white/50">
              {tool.description_vi}
            </p>
          </div>
        </div>

        {/* Action button header */}
        <div className="flex items-center gap-2.5">
          {outputUrl && activeJob?.download_url && (
            <a
              href={activeJob.download_url}
              download
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Download className="w-4 h-4" />
              <span>Tải kết quả</span>
            </a>
          )}

          <button
            type="button"
            disabled={(!inputUrl && !file) || isProcessing}
            onClick={handleExecute}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Đang xử lý ({progressVal}%)...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Xử lý âm thanh</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Main Workbench Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Waveform Workspace & Audio Player (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white dark:bg-[#0B0D12] rounded-2xl border border-slate-200 dark:border-white/[0.08] p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-white/[0.05]">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-white/40">
                Không gian âm thanh
              </span>
              {activeJob?.status === 'done' && (
                <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Xử lý hoàn tất
                </span>
              )}
            </div>

            <AudioWaveformWorkspace
              inputAudioUrl={inputUrl}
              outputAudioUrl={outputUrl}
              inputFileName={inputFileName}
              onFileSelect={handleFileSelect}
              isProcessing={isProcessing}
              progress={progressVal}
              isTrimMode={isTrimTool}
              startTime={startTime}
              endTime={endTime}
              onTrimChange={handleTrimChange}
              availableTools={allTools}
              currentToolId={toolId}
              onChainToTool={handleChainToTool}
            />
          </div>
        </div>

        {/* Right Column: Dynamic Parameters Form (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white dark:bg-[#0B0D12] rounded-2xl border border-slate-200 dark:border-white/[0.08] p-5 shadow-xs space-y-5">
            <DynamicParamsForm
              schema={tool.params_schema}
              values={params}
              onChange={handleParamChange}
              onReset={handleResetParams}
              disabled={isProcessing}
            />

            {/* Estimated cost box */}
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] flex items-center justify-between text-xs">
              <span className="text-slate-500 dark:text-white/60 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" />
                Chi phí ước tính:
              </span>
              <span className="font-semibold text-slate-800 dark:text-white">
                {tool.cost_type === 'free' ? (
                  <span className="text-emerald-600 dark:text-emerald-400">0 credit (Miễn phí)</span>
                ) : (
                  <span className="text-amber-500 font-mono">
                    ~{tool.cost_credits} credit / phút
                  </span>
                )}
              </span>
            </div>

            {/* Bottom Execute Button */}
            <button
              type="button"
              disabled={(!inputUrl && !file) || isProcessing}
              onClick={handleExecute}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Đang xử lý ({progressVal}%)...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Bắt đầu xử lý với {tool.name_vi}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
