import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Developers from './Developers'
import { developersApi } from '../api/developers'
import { ToastProvider } from '../context/ToastContext'

vi.mock('../api/developers', () => ({
  developersApi: {
    listKeys: vi.fn(),
    createKey: vi.fn(),
    revokeKey: vi.fn(),
    getStats: vi.fn(),
  },
}))

describe('Developers Portal Component (Issue #13)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(developersApi.listKeys).mockResolvedValue([
      {
        id: 1,
        name: 'Production Key',
        key_prefix: 'vx_live_abc123...4567',
        is_active: true,
        created_at: '2026-11-09T00:00:00Z',
        last_used_at: null,
        revoked_at: null,
      },
    ])
    vi.mocked(developersApi.getStats).mockResolvedValue({
      total_requests: 150,
      total_credits: 4500,
      daily_usage: [
        { date: '2026-11-08', requests: 50, credits: 1500 },
        { date: '2026-11-09', requests: 100, credits: 3000 },
      ],
    })
  })

  it('renders developer portal tabs and keys table', async () => {
    render(
      <ToastProvider>
        <Developers />
      </ToastProvider>
    )

    expect(screen.getByText(/Cổng Thông Tin Lập Trình Viên/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Quản Lý API Key/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Tài Liệu API v1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Thống Kê Sử Dụng/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Production Key')).toBeInTheDocument()
      expect(screen.getByText('vx_live_abc123...4567')).toBeInTheDocument()
    })
  })

  it('switches to docs tab and shows code snippets', async () => {
    render(
      <ToastProvider>
        <Developers />
      </ToastProvider>
    )

    const docsTabBtn = screen.getByRole('button', { name: /Tài Liệu API v1/i })
    fireEvent.click(docsTabBtn)

    expect(screen.getByText('https://api.voxify.ai/v1')).toBeInTheDocument()
    expect(screen.getAllByText(/GET/i).length).toBeGreaterThan(0)
    expect(screen.getByText('/v1/voices')).toBeInTheDocument()
    expect(screen.getAllByText(/POST/i).length).toBeGreaterThan(0)
  })

  it('switches to stats tab and displays usage metrics', async () => {
    render(
      <ToastProvider>
        <Developers />
      </ToastProvider>
    )

    const statsTabBtn = screen.getByRole('button', { name: /Thống Kê Sử Dụng/i })
    fireEvent.click(statsTabBtn)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText('4,500')).toBeInTheDocument()
    })
  })

  it('opens create key modal and creates new key', async () => {
    vi.mocked(developersApi.createKey).mockResolvedValue({
      id: 2,
      name: 'Mobile App Key',
      key_prefix: 'vx_live_xyz789...9999',
      raw_key: 'vx_live_xyz7891234567890abcdef9999',
      created_at: '2026-11-09T01:00:00Z',
    })

    render(
      <ToastProvider>
        <Developers />
      </ToastProvider>
    )

    const createBtn = screen.getByRole('button', { name: /Tạo API Key Mới/i })
    fireEvent.click(createBtn)

    const input = screen.getByPlaceholderText(/ví dụ: Production Server/i)
    fireEvent.change(input, { target: { value: 'Mobile App Key' } })

    const submitBtn = screen.getByRole('button', { name: /Tạo Khóa Ngay/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/Tạo API Key Thành Công!/i)).toBeInTheDocument()
      expect(screen.getByText('vx_live_xyz7891234567890abcdef9999')).toBeInTheDocument()
    })
  })
})
