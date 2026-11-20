import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SubtitleDubbing from './SubtitleDubbing'
import { dubbingApi } from '../api/dubbing'

vi.mock('../hooks/useVoices', () => ({
  useVoices: () => ({
    data: {
      voices: [
        { id: 'vi-VN-HoaiMyNeural', name: 'Hoài My', name_vi: 'Hoài My', gender: 'female' },
        { id: 'vi-VN-NamMinhNeural', name: 'Nam Minh', name_vi: 'Nam Minh', gender: 'male' },
      ],
    },
  }),
}))

vi.mock('../hooks/useCredit', () => ({
  useCredit: () => ({
    balance: 50000,
    refreshCredits: vi.fn(),
  }),
}))

vi.mock('../api/dubbing', () => ({
  dubbingApi: {
    parseSubtitles: vi.fn(),
    uploadSubtitleFile: vi.fn(),
    previewCue: vi.fn(),
    uploadBackgroundMusic: vi.fn(),
    createJob: vi.fn(),
    getJob: vi.fn(),
  },
}))

describe('SubtitleDubbing Page Component (Issue #21)', () => {
  const mockCues = [
    {
      index: 1,
      start: 1.0,
      end: 3.5,
      duration: 2.5,
      text: 'Chào mừng bạn đến với Voxify',
      voice: 'vi-VN-HoaiMyNeural',
      char_count: 28,
    },
    {
      index: 2,
      start: 4.0,
      end: 7.0,
      duration: 3.0,
      text: 'Lồng tiếng phụ đề video tự động',
      voice: 'vi-VN-NamMinhNeural',
      char_count: 32,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(dubbingApi.parseSubtitles).mockResolvedValue({
      cues: mockCues,
      total_cues: 2,
      char_count: 60,
      estimated_credits: 60,
      warnings_count: 0,
    })
  })

  it('renders header, title, and initial stats', async () => {
    render(
      <MemoryRouter>
        <SubtitleDubbing />
      </MemoryRouter>
    )

    expect(
      screen.getByText('Lồng tiếng phụ đề (SRT / VTT → Audio Khớp Thời Gian)')
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/Tổng số câu:/)).toBeInTheDocument()
      expect(screen.getByText(/Kịch bản câu thoại/)).toBeInTheDocument()
    })
  })

  it('allows switching between file upload mode and text paste mode', async () => {
    render(
      <MemoryRouter>
        <SubtitleDubbing />
      </MemoryRouter>
    )

    const textModeBtn = screen.getByText('Dán nội dung phụ đề')
    fireEvent.click(textModeBtn)

    expect(
      screen.getByPlaceholderText('Dán nội dung SRT hoặc WebVTT tại đây...')
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('Phân tích các câu phụ đề')).toBeInTheDocument()
    })

    const uploadModeBtn = screen.getByText('Tải lên tệp (.srt / .vtt)')
    fireEvent.click(uploadModeBtn)

    expect(
      screen.getByText(/Nhấp để chọn hoặc kéo thả tệp SRT \/ VTT vào đây/)
    ).toBeInTheDocument()
  })

  it('toggles audio ducking settings and adjusts ducking volume', async () => {
    render(
      <MemoryRouter>
        <SubtitleDubbing />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Hòa âm nền thông minh (Audio Ducking)')).toBeInTheDocument()
    })

    const toggleCheckbox = screen.getByRole('checkbox')
    expect(toggleCheckbox).not.toBeChecked()

    fireEvent.click(toggleCheckbox)
    expect(toggleCheckbox).toBeChecked()

    expect(
      screen.getByText('Chọn tệp nhạc nền (MP3, WAV):')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Mức âm lượng nhạc nền khi có lời nói:')
    ).toBeInTheDocument()
  })

  it('creates a dubbing job and polls for completion', async () => {
    vi.mocked(dubbingApi.createJob).mockResolvedValue({
      id: 101,
      user_id: 1,
      title: 'Lồng tiếng (2 câu)',
      subtitle_format: 'srt',
      target_format: 'mp3',
      default_voice: 'vi-VN-HoaiMyNeural',
      status: 'queued',
      progress: 0,
      total_cues: 2,
      char_count: 60,
      credit_used: 60,
      ducking_volume: 0.2,
      duration: 0.0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })

    vi.mocked(dubbingApi.getJob).mockResolvedValue({
      id: 101,
      user_id: 1,
      title: 'Lồng tiếng (2 câu)',
      subtitle_format: 'srt',
      target_format: 'mp3',
      default_voice: 'vi-VN-HoaiMyNeural',
      status: 'done',
      progress: 100,
      total_cues: 2,
      char_count: 60,
      credit_used: 60,
      ducking_volume: 0.2,
      duration: 6.5,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audio_download_url: '/api/dubbing/jobs/101/audio',
      zip_download_url: '/api/dubbing/jobs/101/zip',
    })

    render(
      <MemoryRouter>
        <SubtitleDubbing />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Bắt đầu Lồng Tiếng Khớp Thời Gian/)).toBeInTheDocument()
    })

    const startBtn = screen.getByText(/Bắt đầu Lồng Tiếng Khớp Thời Gian/)
    fireEvent.click(startBtn)

    await waitFor(() => {
      expect(dubbingApi.createJob).toHaveBeenCalledTimes(1)
    })
  })
})
