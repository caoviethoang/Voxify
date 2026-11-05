import { useState, useEffect, useRef, useCallback } from 'react'
import {
  createTTSJob,
  getTTSJob,
  type TTSJob,
  type CreateTTSJobParams,
  getJobAudioUrl,
  getJobSubtitleUrl,
} from '../api/tts'
import { useAuth } from './useAuth'

const ACTIVE_JOB_KEY = 'voxify_active_tts_job_id'

export function useTTSJob() {
  const { refreshUser } = useAuth()
  const [activeJob, setActiveJob] = useState<TTSJob | null>(null)
  const [isJobRunning, setIsJobRunning] = useState<boolean>(false)
  const [jobProgress, setJobProgress] = useState<number>(0)
  const [jobError, setJobError] = useState<string | null>(null)

  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const activeJobIdRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  // Poll trạng thái của job
  const pollJobStatus = useCallback(
    async (jobId: number) => {
      try {
        const job = await getTTSJob(jobId)
        setActiveJob(job)
        setJobProgress(job.progress)

        if (job.status === 'done') {
          stopPolling()
          setIsJobRunning(false)
          setJobError(null)
          refreshUser()
        } else if (job.status === 'failed') {
          stopPolling()
          setIsJobRunning(false)
          setJobError(job.error_message || 'Tạo giọng nói thất bại.')
          refreshUser()
        }
      } catch (err: unknown) {
        // Tạm thời bỏ qua lỗi mạng lẻ trong khi poll
        console.warn('Lỗi khi kiểm tra tiến độ job:', err)
      }
    },
    [stopPolling, refreshUser]
  )

  // Bắt đầu một Job mới
  const startJob = useCallback(
    async (params: CreateTTSJobParams) => {
      stopPolling()
      setIsJobRunning(true)
      setJobProgress(5)
      setJobError(null)

      try {
        const job = await createTTSJob(params)
        setActiveJob(job)
        activeJobIdRef.current = job.id
        localStorage.setItem(ACTIVE_JOB_KEY, job.id.toString())

        // Bắt đầu polling mỗi 800ms
        pollingRef.current = setInterval(() => {
          pollJobStatus(job.id)
        }, 800)

        return job
      } catch (err: unknown) {
        setIsJobRunning(false)
        stopPolling()
        let msg = 'Có lỗi xảy ra khi khởi tạo tác vụ.'
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { data?: { detail?: string } } }
          msg = axiosErr.response?.data?.detail || msg
        } else if (err instanceof Error) {
          msg = err.message
        }
        setJobError(msg)
        throw new Error(msg)
      }
    },
    [stopPolling, pollJobStatus]
  )

  // Khôi phục Job đang chạy hoặc vừa hoàn thành khi mở/F5 lại trang
  useEffect(() => {
    const savedJobId = localStorage.getItem(ACTIVE_JOB_KEY)
    if (savedJobId) {
      const jobId = parseInt(savedJobId, 10)
      if (!isNaN(jobId)) {
        activeJobIdRef.current = jobId
        getTTSJob(jobId)
          .then((job) => {
            setActiveJob(job)
            setJobProgress(job.progress)
            if (job.status === 'queued' || job.status === 'processing') {
              setIsJobRunning(true)
              pollingRef.current = setInterval(() => {
                pollJobStatus(jobId)
              }, 800)
            } else if (job.status === 'failed') {
              setJobError(job.error_message || 'Tác vụ đã thất bại.')
            }
          })
          .catch(() => {
            localStorage.removeItem(ACTIVE_JOB_KEY)
          })
      }
    }

    return () => {
      stopPolling()
    }
  }, [pollJobStatus, stopPolling])

  const clearJob = useCallback(() => {
    stopPolling()
    setActiveJob(null)
    setIsJobRunning(false)
    setJobProgress(0)
    setJobError(null)
    localStorage.removeItem(ACTIVE_JOB_KEY)
  }, [stopPolling])

  return {
    activeJob,
    isJobRunning,
    jobProgress,
    jobError,
    startJob,
    clearJob,
    getJobAudioUrl,
    getJobSubtitleUrl,
  }
}
