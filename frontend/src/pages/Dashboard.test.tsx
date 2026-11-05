import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from './Dashboard'
import * as dashboardApi from '../api/dashboard'

vi.mock('../api/dashboard', () => ({
  fetchDashboardStats: vi.fn(),
}))

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 1, full_name: 'Việt Hoàng', email: 'hoang@example.com' },
  }),
}))

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state while loading stats', () => {
    vi.mocked(dashboardApi.fetchDashboardStats).mockReturnValue(new Promise(() => {}))

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    expect(screen.getByText('Đang tải tác vụ gần nhất...')).toBeInTheDocument()
  })

  it('renders stats and user greeting when fetchDashboardStats succeeds', async () => {
    const mockData: dashboardApi.DashboardStats = {
      chars_used_this_month: 25400,
      total_audio_generated: 48,
      total_duration_seconds: 360,
      credit_balance: 8450,
      latest_generation: {
        id: 12,
        title: 'Dự án giới thiệu sản phẩm',
        text: 'Nội dung dự án TTS',
        voice: 'vi-VN-HoaiMyNeural',
        format: 'mp3',
        duration: 35,
        char_count: 120,
        status: 'done',
        progress: 100,
        credit_used: 120,
        audio_url: 'http://test/12.mp3',
        rate: '+0%',
        pitch: '+0Hz',
        volume: '+0%',
        is_preview: false,
        created_at: '2026-01-01T00:00:00Z',
      },
      recent_activities: [],
    }

    vi.mocked(dashboardApi.fetchDashboardStats).mockResolvedValueOnce(mockData)

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Việt Hoàng', { exact: false })).toBeInTheDocument()
      expect(screen.getByText('48')).toBeInTheDocument()
      expect(screen.getByText('Dự án giới thiệu sản phẩm')).toBeInTheDocument()
      expect(screen.getByText('6 phút')).toBeInTheDocument()
    })
  })

  it('renders error message when fetch fails', async () => {
    vi.mocked(dashboardApi.fetchDashboardStats).mockRejectedValueOnce(
      new Error('Lỗi kết nối máy chủ')
    )

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Lỗi kết nối máy chủ')).toBeInTheDocument()
    })
  })
})
