import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TextToSpeech from './TextToSpeech'

// Mock hooks
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 1, full_name: 'Hoàng Cao', email: 'hoangcv17@gmail.com' },
  }),
}))

vi.mock('../hooks/useAppConfig', () => ({
  useAppConfig: () => ({
    config: {
      default_voice: 'vi-VN-HoaiMyNeural',
      max_chars: 100000,
      char_multiplier: 1,
      min_recharge_vnd: 20000,
      vnd_per_credit: 1,
    },
  }),
}))

vi.mock('../hooks/useVoices', () => ({
  useVoices: () => ({
    data: {
      voices: [
        {
          id: 'vi-VN-HoaiMyNeural',
          name: 'Hoài My',
          gender: 'Female',
          locale: 'vi-VN',
          language: 'vi-VN',
          provider: 'edge',
          country_flag: '🇻🇳',
        },
        {
          id: 'vi-VN-NamMinhNeural',
          name: 'Nam Minh',
          gender: 'Male',
          locale: 'vi-VN',
          language: 'vi-VN',
          provider: 'edge',
          country_flag: '🇻🇳',
        },
      ],
    },
    isLoading: false,
  }),
}))

vi.mock('../hooks/useTTS', () => ({
  useTTS: () => ({
    generate: vi.fn(),
    isGenerating: false,
    audioUrl: null,
    history: [],
    reloadHistory: vi.fn(),
  }),
}))

vi.mock('../hooks/useTTSJob', () => ({
  useTTSJob: () => ({
    job: null,
    isPolling: false,
    cancelJob: vi.fn(),
  }),
}))

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

vi.mock('../api/tts', () => ({
  listRecentJobs: vi.fn().mockResolvedValue([
    {
      id: 'job-1',
      title: 'Tập 1: Giới thiệu hệ thống',
      text: 'Chào mừng các bạn đến với ứng dụng đọc văn bản Voxify.',
      voice: 'vi-VN-HoaiMyNeural',
      format: 'mp3',
      duration: 12.5,
      char_count: 58,
      status: 'done',
      progress: 100,
      credit_used: 58,
      audio_url: 'https://cdn.voxify.local/audio/job-1.mp3',
      rate: '+0%',
      pitch: '+0Hz',
      volume: '+0%',
      is_preview: false,
      created_at: '2026-11-05T08:00:00Z',
    },
  ]),
}))

describe('TextToSpeech Studio Page (Issue #32)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders full-height text editor with correct placeholder and toolbar pills', () => {
    render(
      <MemoryRouter>
        <TextToSpeech />
      </MemoryRouter>
    )

    // Full-height editor textarea
    const textarea = screen.getByPlaceholderText(
      'Nhập hoặc dán nội dung văn bản cần chuyển đổi thành giọng nói...'
    )
    expect(textarea).toBeInTheDocument()

    // Mode toolbar pills
    expect(screen.getByText('Đơn giọng')).toBeInTheDocument()
    expect(screen.getByText('Nhiều giọng')).toBeInTheDocument()
    expect(screen.getByText('Phụ đề')).toBeInTheDocument()
    expect(screen.getByText('Kịch bản')).toBeInTheDocument()
  })

  it('renders sidebar tabs (Cấu hình & Lịch sử) and shows settings by default', () => {
    render(
      <MemoryRouter>
        <TextToSpeech />
      </MemoryRouter>
    )

    expect(screen.getByRole('button', { name: /Cấu hình/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Lịch sử/i })).toBeInTheDocument()

    // Quick emotion/audio chips
    expect(screen.getByText('Cười')).toBeInTheDocument()
    expect(screen.getByText('Thở dài')).toBeInTheDocument()
    expect(screen.getByText('Hắng giọng')).toBeInTheDocument()
    expect(screen.getByText(/Tạm dừng/i)).toBeInTheDocument()

    // Speed slider
    expect(screen.getByText('Tốc độ đọc')).toBeInTheDocument()
  })

  it('switches to Lịch sử tab and displays search and history cards', async () => {
    render(
      <MemoryRouter>
        <TextToSpeech />
      </MemoryRouter>
    )

    const historyTabBtn = screen.getByRole('button', { name: /Lịch sử/i })
    fireEvent.click(historyTabBtn)

    // Check search input
    expect(
      screen.getByPlaceholderText('Tìm kiếm theo nội dung, ID...')
    ).toBeInTheDocument()

    // Wait for history item to render
    await waitFor(() => {
      expect(
        screen.getByText(/Chào mừng các bạn đến với ứng dụng đọc văn bản Voxify/i)
      ).toBeInTheDocument()
      expect(screen.getByText('12.5s')).toBeInTheDocument()
    })
  })

  it('inserts emotion tag into the textarea when emotion chip is clicked', () => {
    render(
      <MemoryRouter>
        <TextToSpeech />
      </MemoryRouter>
    )

    const textarea = screen.getByPlaceholderText(
      'Nhập hoặc dán nội dung văn bản cần chuyển đổi thành giọng nói...'
    ) as HTMLTextAreaElement

    fireEvent.change(textarea, { target: { value: 'Xin chào bạn' } })

    const laughButton = screen.getByText('Cười')
    fireEvent.click(laughButton)

    expect(textarea.value).toContain('[cười]')
  })
})
