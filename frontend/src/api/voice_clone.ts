import apiClient from './client'

export interface ClonedVoice {
  id: number
  voice_id: string
  user_id: number
  name: string
  description?: string
  sample_duration: number
  sample_size_bytes: number
  quality_score?: number
  gender: string
  language: string
  provider: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
  preview_url?: string
  preview_audio_url?: string
  sample_url?: string
}

export interface VoiceCloneQuota {
  used: number
  max_allowed: number
  plan_name: string
  creation_fee: number
  multiplier: number
}

export interface ClonedVoiceListResponse {
  total: number
  quota: VoiceCloneQuota
  voices: ClonedVoice[]
}

export interface VoiceAbuseReportRequest {
  reason: 'celebrity_impersonation' | 'no_consent' | 'copyright' | 'defamation' | 'other'
  description: string
  reporter_email?: string
}

export async function listClonedVoices(): Promise<ClonedVoiceListResponse> {
  const res = await apiClient.get<ClonedVoiceListResponse>('/api/voices/cloned')
  return res.data
}

export async function getVoiceCloneLimits(): Promise<VoiceCloneQuota> {
  const res = await apiClient.get<VoiceCloneQuota>('/api/voices/clone/limits')
  return res.data
}

export async function createVoiceClone(formData: FormData): Promise<ClonedVoice> {
  const res = await apiClient.post<ClonedVoice>('/api/voices/clone', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
}

export async function updateClonedVoice(
  voiceId: string,
  data: { name?: string; description?: string }
): Promise<ClonedVoice> {
  const res = await apiClient.patch<ClonedVoice>(`/api/voices/cloned/${voiceId}`, data)
  return res.data
}

export async function deleteClonedVoice(
  voiceId: string
): Promise<{ success: boolean; message: string }> {
  const res = await apiClient.delete<{ success: boolean; message: string }>(
    `/api/voices/cloned/${voiceId}`
  )
  return res.data
}

export async function reportVoiceAbuse(
  voiceId: string,
  data: VoiceAbuseReportRequest
): Promise<{ id: number; status: string }> {
  const res = await apiClient.post<{ id: number; status: string }>(
    `/api/voices/cloned/${voiceId}/report`,
    data
  )
  return res.data
}

export function getClonedVoicePreviewUrl(voiceId: string): string {
  return `/api/voices/cloned/${voiceId}/preview`
}

export function getClonedVoiceSampleUrl(voiceId: string): string {
  return `/api/voices/cloned/${voiceId}/sample`
}
