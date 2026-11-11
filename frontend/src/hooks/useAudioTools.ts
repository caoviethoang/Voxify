import { useQuery } from '@tanstack/react-query'
import {
  fetchAudioTools,
  fetchAudioTool,
  fetchAudioToolJobs,
  fetchAudioToolJob,
  type AudioToolListResponse,
  type AudioTool,
  type AudioToolJob,
} from '../api/audio_tools'

export function useAudioTools() {
  return useQuery<AudioToolListResponse>({
    queryKey: ['audio-tools'],
    queryFn: fetchAudioTools,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAudioTool(toolId?: string) {
  return useQuery<AudioTool>({
    queryKey: ['audio-tool', toolId],
    queryFn: () => {
      if (!toolId) throw new Error('Tool ID is required')
      return fetchAudioTool(toolId)
    },
    enabled: Boolean(toolId),
    staleTime: 5 * 60 * 1000,
  })
}

export function useAudioToolJobs(toolId?: string) {
  return useQuery<AudioToolJob[]>({
    queryKey: ['audio-tool-jobs', toolId],
    queryFn: () => fetchAudioToolJobs(toolId),
  })
}

export function useAudioToolJob(jobId: string | null) {
  return useQuery<AudioToolJob>({
    queryKey: ['audio-tool-job', jobId],
    queryFn: () => {
      if (!jobId) throw new Error('Job ID is required')
      return fetchAudioToolJob(jobId)
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'queued' || status === 'processing') {
        return 1000 // Poll every 1s while active
      }
      return false
    },
  })
}
