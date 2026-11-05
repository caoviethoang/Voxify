import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HistoryPage from './History'
import { historyApi } from '../api/history'

vi.mock('../api/history', () => ({
  historyApi: {
    list: vi.fn(),
    deleteOne: vi.fn(),
    deleteBulk: vi.fn(),
    updateTitle: vi.fn(),
  },
}))

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

const mockHistoryResponse = {
  items: [
    {
      id: 101,
      title: 'Bản tin tài chính sáng',
      text: 'Thị trường chứng khoán hôm nay có nhiều biến động tích cực.',
      voice: 'vi-VN-HoaiMyNeural',
      format: 'mp3',
      duration: 18.5,
      char_count: 58,
      status: 'done' as const,
      progress: 100,
      credit_used: 58,
      audio_url: 'http://test/101.mp3',
      rate: '+0%',
      pitch: '+0Hz',
      volume: '+0%',
      is_preview: false,
      created_at: '2026-02-01T08:00:00Z',
    },
    {
      id: 102,
      title: 'Truyện ngụ ngôn',
      text: 'Ngày xửa ngày xưa ở một ngôi làng nọ.',
      voice: 'vi-VN-NamMinhNeural',
      format: 'mp3',
      duration: 25.0,
      char_count: 36,
      status: 'done' as const,
      progress: 100,
      credit_used: 36,
      audio_url: 'http://test/102.mp3',
      rate: '+0%',
      pitch: '+0Hz',
      volume: '+0%',
      is_preview: false,
      created_at: '2026-02-01T09:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  limit: 15,
  pages: 1,
}

describe('History Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders history items with titles, voice name, and duration', async () => {
    vi.mocked(historyApi.list).mockResolvedValueOnce(mockHistoryResponse)

    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Bản tin tài chính sáng')).toBeInTheDocument()
      expect(screen.getByText('Truyện ngụ ngôn')).toBeInTheDocument()
      expect(screen.getByText('vi-VN-HoaiMyNeural')).toBeInTheDocument()
      expect(screen.getByText('vi-VN-NamMinhNeural')).toBeInTheDocument()
      expect(screen.getByText('0:18')).toBeInTheDocument()
      expect(screen.getByText('0:25')).toBeInTheDocument()
    })
  })

  it('allows selecting rows and batch selection toggle', async () => {
    vi.mocked(historyApi.list).mockResolvedValueOnce(mockHistoryResponse)

    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Bản tin tài chính sáng')).toBeInTheDocument()
    })

    const selectAllBtn = screen.getByRole('button', { name: 'Chọn tất cả' })
    const selectItem1Btn = screen.getByRole('button', { name: 'Chọn bản ghi 101' })

    expect(selectAllBtn).toBeInTheDocument()
    expect(selectItem1Btn).toBeInTheDocument()

    // Select row 1
    fireEvent.click(selectItem1Btn)

    // Select all
    fireEvent.click(selectAllBtn)
  })

  it('shows empty state when no history items exist', async () => {
    vi.mocked(historyApi.list).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      limit: 15,
      pages: 1,
    })

    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Chưa có lịch sử xử lý nào/i)).toBeInTheDocument()
    })
  })
})
