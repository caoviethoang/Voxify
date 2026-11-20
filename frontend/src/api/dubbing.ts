import client from './client'

export interface SubtitleCueItem {
  index: number
  start: number
  end: number
  duration: number
  text: string
  voice: string
  original_voice_tag?: string | null
  char_count: number
  actual_duration?: number | null
  adjusted_tempo?: number | null
  warning?: string | null
  audio_url?: string | null
}

export interface DubbingParseResponse {
  cues: SubtitleCueItem[]
  total_cues: number
  char_count: number
  estimated_credits: number
  warnings_count: number
}

export interface DubbingCreateJobRequest {
  title: string
  subtitle_format: 'srt' | 'vtt'
  target_format: 'mp3' | 'wav'
  default_voice: string
  cues: SubtitleCueItem[]
  ducking_volume: number
  background_audio_path?: string | null
}

export interface DubbingJob {
  id: number
  user_id: number
  title: string
  subtitle_format: string
  target_format: string
  default_voice: string
  status: 'queued' | 'processing' | 'done' | 'failed'
  progress: number
  total_cues: number
  char_count: number
  credit_used: number
  cues_data?: string | null
  output_audio_path?: string | null
  output_zip_path?: string | null
  background_audio_path?: string | null
  ducking_volume: number
  error_message?: string | null
  duration: number
  created_at: string
  updated_at: string
  audio_download_url?: string | null
  zip_download_url?: string | null
}

export interface BackgroundMusicUploadResponse {
  background_audio_path: string
  filename: string
  size: number
}

export interface PreviewCueResult {
  audioBlob: Blob
  actualDuration: number
  adjustedTempo: number
  warning?: string | null
}

export const dubbingApi = {
  /**
   * Phân tích nội dung thô phụ đề SRT/VTT thành danh sách Cue
   */
  async parseSubtitles(content: string, defaultVoice = 'vi-VN-HoaiMyNeural'): Promise<DubbingParseResponse> {
    const res = await client.post<DubbingParseResponse>('/api/dubbing/parse', {
      content,
      default_voice: defaultVoice,
    })
    return res.data
  },

  /**
   * Tải tệp .srt hoặc .vtt lên và nhận kết quả phân tích
   */
  async uploadSubtitleFile(file: File, defaultVoice = 'vi-VN-HoaiMyNeural'): Promise<DubbingParseResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('default_voice', defaultVoice)

    const res = await client.post<DubbingParseResponse>('/api/dubbing/upload-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  /**
   * Nghe thử một câu phụ đề riêng lẻ
   */
  async previewCue(text: string, voice: string, targetDuration?: number): Promise<PreviewCueResult> {
    const res = await client.post(
      '/api/dubbing/preview-cue',
      {
        text,
        voice,
        target_duration: targetDuration,
      },
      {
        responseType: 'blob',
      }
    )

    const actualDuration = parseFloat(res.headers['x-actual-duration'] || '0')
    const adjustedTempo = parseFloat(res.headers['x-adjusted-tempo'] || '1.0')
    const warning = res.headers['x-tempo-warning']
      ? decodeURIComponent(escape(res.headers['x-tempo-warning']))
      : null

    return {
      audioBlob: res.data as Blob,
      actualDuration,
      adjustedTempo,
      warning,
    }
  },

  /**
   * Tải tệp nhạc nền phục vụ hòa âm Audio Ducking
   */
  async uploadBackgroundMusic(file: File): Promise<BackgroundMusicUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const res = await client.post<BackgroundMusicUploadResponse>('/api/dubbing/upload-bg-music', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  /**
   * Khởi tạo tác vụ lồng tiếng phụ đề
   */
  async createJob(payload: DubbingCreateJobRequest): Promise<DubbingJob> {
    const res = await client.post<DubbingJob>('/api/dubbing/jobs', payload)
    return res.data
  },

  /**
   * Lấy chi tiết tác vụ theo ID
   */
  async getJob(jobId: number): Promise<DubbingJob> {
    const res = await client.get<DubbingJob>(`/api/dubbing/jobs/${jobId}`)
    return res.data
  },

  /**
   * Lấy danh sách tác vụ lồng tiếng
   */
  async listJobs(limit = 20, offset = 0): Promise<DubbingJob[]> {
    const res = await client.get<DubbingJob[]>('/api/dubbing/jobs', {
      params: { limit, offset },
    })
    return res.data
  },

  /**
   * Xóa tác vụ lồng tiếng
   */
  async deleteJob(jobId: number): Promise<void> {
    await client.delete(`/api/dubbing/jobs/${jobId}`)
  },
}
