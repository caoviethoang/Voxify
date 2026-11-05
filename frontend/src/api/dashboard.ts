import client from './client'
import { type HistoryItem } from './history'

export interface DashboardStats {
  chars_used_this_month: number
  total_audio_generated: number
  total_duration_seconds: number
  credit_balance: number
  latest_generation: HistoryItem | null
  recent_activities: HistoryItem[]
}

/**
 * Lấy dữ liệu thống kê và hoạt động gần đây cho trang Dashboard
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await client.get<DashboardStats>('/dashboard/stats')
  return data
}

export const dashboardApi = {
  getStats: fetchDashboardStats,
}

