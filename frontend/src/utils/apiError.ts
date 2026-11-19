import axios from 'axios'

/**
 * Bóc tách thông điệp lỗi trực quan từ các đối tượng lỗi API, AxiosError, hoặc Error tiêu chuẩn.
 *
 * @param error - Đối tượng lỗi bất kỳ (unknown)
 * @param fallbackMessage - Thông điệp dự phòng khi không trích xuất được (mặc định: 'Đã có lỗi xảy ra.')
 * @returns Chuỗi thông báo lỗi người dùng có thể đọc hiểu
 */
export function extractApiErrorMessage(
  error: unknown,
  fallbackMessage: string = 'Đã có lỗi xảy ra.'
): string {
  if (!error) return fallbackMessage

  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    if (typeof data === 'string' && data.trim()) {
      return data
    }
    if (data && typeof data === 'object') {
      const detail = (data as { detail?: unknown }).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0]
        if (typeof first === 'object' && first !== null && 'msg' in first && typeof first.msg === 'string') {
          return first.msg
        }
      }
      const errObj = (data as { error?: { message?: unknown } }).error
      if (errObj && typeof errObj.message === 'string' && errObj.message.trim()) {
        return errObj.message
      }
      const message = (data as { message?: unknown }).message
      if (typeof message === 'string' && message.trim()) {
        return message
      }
    }
    if (error.message) {
      return error.message
    }
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  if (typeof error === 'string' && error.trim()) {
    return error
  }

  return fallbackMessage
}
