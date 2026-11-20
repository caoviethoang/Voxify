/**
 * Tiện ích định dạng thời gian và ngày tháng dùng chung cho toàn bộ Frontend.
 */

/**
 * Định dạng thời lượng từ giây sang mm:ss (hoặc m:ss nếu padMinutes = false).
 * @param seconds - Số giây cần định dạng
 * @param padMinutes - Có đệm số 0 ở đầu phần phút hay không (mặc định false: '0:18', true: '00:18')
 */
export function formatDuration(seconds: number, padMinutes: boolean = false): string {
  if (!seconds || isNaN(seconds) || seconds < 0) {
    return padMinutes ? '00:00' : '0:00'
  }
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const minStr = padMinutes ? mins.toString().padStart(2, '0') : mins.toString()
  const secStr = secs.toString().padStart(2, '0')
  return `${minStr}:${secStr}`
}

/**
 * Định dạng tổng thời lượng tích lũy sang định dạng thân thiện cho dashboard.
 * Ví dụ: '6 phút', '2 giờ 15 phút', '45 giây', '0 giây'.
 */
export function formatTotalDuration(seconds: number): string {
  if (!seconds || seconds <= 0 || isNaN(seconds)) return '0 giây'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return minutes > 0 ? `${hours} giờ ${minutes} phút` : `${hours} giờ`
  }
  if (minutes > 0) {
    return secs > 0 ? `${minutes} phút ${secs}s` : `${minutes} phút`
  }
  return `${secs} giây`
}

/**
 * Định dạng thời gian tương đối so với hiện tại.
 * Ví dụ: 'vừa xong', '5 phút trước', '2 giờ trước', '3 ngày trước', 'DD/MM/YYYY'.
 */
export function formatRelativeTime(dateStr?: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  if (diffSecs < 60) return 'vừa xong'
  const diffMins = Math.floor(diffSecs / 60)
  if (diffMins < 60) return `${diffMins} phút trước`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} giờ trước`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays} ngày trước`
  return date.toLocaleDateString('vi-VN')
}

/**
 * Định dạng ngày giờ theo định dạng bản địa hóa tiếng Việt.
 * Ví dụ: '01/02/2026, 08:00'.
 */
export function formatDate(dateStr?: string, includeTime: boolean = true): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  if (!includeTime) {
    return date.toLocaleDateString('vi-VN')
  }
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
