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

export interface TTSJob {
  id: number
  status: 'queued' | 'processing' | 'done' | 'failed'
  progress: number
  text: string
  char_count: number
  duration: number
  format: 'mp3' | 'wav'
  credit_used: number
  voice: string
  rate?: string
  pitch?: string
  volume?: string
  error_message?: string | null
  audio_url?: string | null
  srt_url?: string | null
  vtt_url?: string | null
  created_at: string
  updated_at: string
}

export interface CreateTTSJobParams {
  text: string
  voice: string
  rate?: string
  pitch?: string
  volume?: string
  format?: 'mp3' | 'wav'
  apply_dictionary?: boolean
}

export async function fetchVoices(): Promise<VoiceListResponse> {
  const { data } = await client.get<VoiceListResponse>('/voices')
  return data
}

export async function synthesize(
  params: SynthesizeParams
): Promise<Blob & { creditBalance?: number; creditUsed?: number; duration?: number }> {
  const response = await client.post('/tts', params, {
    responseType: 'blob',
  })
  const blob = response.data as Blob & { creditBalance?: number; creditUsed?: number; duration?: number }

  const balHeader = response.headers['x-credit-balance']
  if (balHeader !== undefined) {
    blob.creditBalance = parseInt(balHeader, 10)
  }

  const usedHeader = response.headers['x-credit-used']
  if (usedHeader !== undefined) {
    blob.creditUsed = parseInt(usedHeader, 10)
  }

  const durHeader = response.headers['x-duration']
  if (durHeader !== undefined) {
    blob.duration = parseFloat(durHeader)
  }

  return blob
}

/** Tạo Background Job Text to Speech bất đồng bộ */
export async function createTTSJob(params: CreateTTSJobParams): Promise<TTSJob> {
  const { data } = await client.post<TTSJob>('/tts/jobs', params)
  return data
}

/** Lấy thông tin trạng thái & tiến độ Job TTS */
export async function getTTSJob(jobId: number): Promise<TTSJob> {
  const { data } = await client.get<TTSJob>(`/tts/jobs/${jobId}`)
  return data
}

/** Lấy danh sách các Job gần đây của người dùng */
export async function listRecentJobs(limit = 10): Promise<TTSJob[]> {
  const { data } = await client.get<TTSJob[]>('/tts/jobs', { params: { limit } })
  return data
}

/** Đường dẫn stream / download audio của Job */
export function getJobAudioUrl(jobId: number, download = false): string {
  const base = client.defaults.baseURL || '/api'
  return `${base}/tts/jobs/${jobId}/audio${download ? '?download=true' : ''}`
}

/** Đường dẫn tải phụ đề SRT hoặc VTT của Job */
export function getJobSubtitleUrl(jobId: number, format: 'srt' | 'vtt'): string {
  const base = client.defaults.baseURL || '/api'
  return `${base}/tts/jobs/${jobId}/subtitles?format=${format}`
}
