import client from './client'

export interface Voice {
  id: string
  name: string
  full_name?: string
  gender: string
  locale: string
  locale_name?: string
  is_vietnamese: boolean
  suggested_codec?: string
}

export interface VoiceListResponse {
  voices: Voice[]
  total: number
  vietnamese_count: number
}

export interface SynthesizeParams {
  text: string
  voice: string
  rate: string
  pitch: string
  volume: string
  preview?: boolean
}

export async function fetchVoices(): Promise<VoiceListResponse> {
  const { data } = await client.get<VoiceListResponse>('/voices')
  return data
}

export async function synthesize(params: SynthesizeParams): Promise<Blob> {
  const response = await client.post('/tts', params, {
    responseType: 'blob',
  })
  return response.data as Blob
}
