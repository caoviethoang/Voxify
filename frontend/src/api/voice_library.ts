import client from './client'

export interface VoiceLibraryItem {
  id: number
  owner_id: number | null
  name: string
  display_name: string | null
  description: string | null
  provider: string
  provider_voice_id: string | null
  voice_type: 'system' | 'cloned' | 'imported' | string
  language: string
  gender: string
  tags: string | null
  preview_url: string | null
  sample_duration: number | null
  visibility: string
  status: string
  is_active: boolean
  tier: 'free' | 'premium' | string
  credit_multiplier: number
  cloned_voice_ref: string | null
  total_uses: number
  created_at: string
  is_favorite: boolean
}

export interface VoiceLibraryListResponse {
  total: number
  voices: VoiceLibraryItem[]
  favorite_ids: number[]
}

export interface ToggleFavoriteResponse {
  voice_id: number
  is_favorite: boolean
  message: string
}

export interface SyncVoicesResponse {
  synced: number
  message: string
}

export interface VoiceUpdateRequest {
  is_active?: boolean
  tier?: string
  credit_multiplier?: number
  tags?: string
  display_name?: string
}

export interface FetchVoiceLibraryParams {
  tab?: 'all' | 'mine' | 'favorites'
  voice_type?: string
  language?: string
  gender?: string
  search?: string
  limit?: number
  offset?: number
}

export async function fetchVoiceLibrary(
  params?: FetchVoiceLibraryParams
): Promise<VoiceLibraryListResponse> {
  const response = await client.get<VoiceLibraryListResponse>('/voices/library', {
    params,
  })
  return response.data
}

export async function toggleVoiceFavorite(voiceId: number): Promise<ToggleFavoriteResponse> {
  const response = await client.post<ToggleFavoriteResponse>(`/voices/library/${voiceId}/favorite`)
  return response.data
}

export async function getFavoriteVoiceIds(): Promise<number[]> {
  const response = await client.get<number[]>('/voices/favorites')
  return response.data
}

export async function syncSystemVoices(): Promise<SyncVoicesResponse> {
  const response = await client.post<SyncVoicesResponse>('/voices/library/sync')
  return response.data
}

export async function updateVoice(
  voiceId: number,
  data: VoiceUpdateRequest
): Promise<VoiceLibraryItem> {
  const response = await client.patch<VoiceLibraryItem>(`/voices/library/${voiceId}`, data)
  return response.data
}
