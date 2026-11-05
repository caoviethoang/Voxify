import client from './client'

export interface HistoryItem {
  id: number
  title: string
  text: string
  voice: string
  rate: string
  pitch: string
  volume: string
  format: string
  duration: number
  char_count: number
  credit_used: number
  status: 'queued' | 'processing' | 'done' | 'failed'
  progress: number
  error_message?: string
  audio_url?: string
  srt_url?: string
  vtt_url?: string
  is_preview: boolean
  created_at?: string
  updated_at?: string
}

export interface HistoryListParams {
  page?: number
  limit?: number
  status?: string
  search?: string
  date_from?: string
  date_to?: string
  format?: string
}

export interface HistoryListResponse {
  items: HistoryItem[]
  total: number
  page: number
  limit: number
  pages: number
}

/**
 * Lấy danh sách lịch sử xử lý TTS (có phân trang và bộ lọc)
 */
export async function fetchHistory(params: HistoryListParams = {}): Promise<HistoryListResponse> {
  const { data } = await client.get<HistoryListResponse>('/history', { params })
  return data
}

/**
 * Xóa một bản ghi lịch sử theo ID
 */
export async function deleteHistoryItem(id: number): Promise<void> {
  await client.delete(`/history/${id}`)
}

/**
 * Xóa nhiều bản ghi lịch sử theo danh sách ID
 */
export async function deleteHistoryBulk(ids: number[]): Promise<void> {
  await client.delete('/history/bulk', { data: { ids } })
}

/**
 * Cập nhật tiêu đề của một bản ghi lịch sử
 */
export async function updateHistoryTitle(id: number, title: string): Promise<HistoryItem> {
  const { data } = await client.patch<HistoryItem>(`/history/${id}`, { title })
  return data
}

export const historyApi = {
  list: fetchHistory,
  deleteOne: deleteHistoryItem,
  deleteBulk: deleteHistoryBulk,
  updateTitle: updateHistoryTitle,
}
