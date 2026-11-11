import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AudioToolsHub from './AudioToolsHub'
import * as toolsHook from '../hooks/useAudioTools'
import type { AudioToolListResponse, AudioToolJob } from '../api/audio_tools'

vi.mock('../hooks/useAudioTools', () => ({
  useAudioTools: vi.fn(),
  useAudioToolJobs: vi.fn(),
}))

describe('AudioToolsHub Page', () => {
  const mockToolsData: AudioToolListResponse = {
    total_tools: 2,
    categories: [
      {
        category: 'trim_cut',
        meta: {
          id: 'trim_cut',
          title_vi: 'Cắt & Ghép',
          title_en: 'Trim & Cut',
          icon: 'scissors',
          order: 1,
        },
        tools: [
          {
            id: 'trim',
            name_vi: 'Cắt Audio chính xác',
            name_en: 'Audio Trimmer',
            category: 'trim_cut',
            icon: 'scissors',
            cost_type: 'free',
            cost_credits: 0,
            heavy: false,
            description_vi: 'Cắt audio theo mili-giây, hỗ trợ fade-in/fade-out.',
            description_en: 'Trim audio with millisecond precision.',
            params_schema: { type: 'object', properties: {} },
          },
        ],
      },
      {
        category: 'ai_separation',
        meta: {
          id: 'ai_separation',
          title_vi: 'Tách âm AI',
          title_en: 'AI Separation',
          icon: 'music',
          order: 5,
        },
        tools: [
          {
            id: 'ai_vocal_remover',
            name_vi: 'Tách lời & beat AI',
            name_en: 'AI Vocal Remover',
            category: 'ai_separation',
            icon: 'music',
            cost_type: 'per_minute',
            cost_credits: 2,
            heavy: true,
            description_vi: 'Tách vocal bài hát và nhạc nền bằng mô hình AI.',
            description_en: 'Separate vocals and instrumentals.',
            params_schema: { type: 'object', properties: {} },
          },
        ],
      },
    ],
  }

  const mockJobs: AudioToolJob[] = [
    {
      id: 'job-12345678-abcd',
      user_id: 1,
      tool_id: 'trim',
      tool_name_vi: 'Cắt Audio chính xác',
      status: 'done',
      progress: 100,
      input_filename: 'speech.mp3',
      credit_used: 0,
      created_at: '2026-11-11T10:00:00Z',
      updated_at: '2026-11-11T10:00:01Z',
      stream_url: '/api/tools/jobs/job-12345678-abcd/stream',
      download_url: '/api/tools/jobs/job-12345678-abcd/download',
    },
  ]

  it('renders tool list and filters by search query', () => {
    vi.mocked(toolsHook.useAudioTools).mockReturnValue({
      data: mockToolsData,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof toolsHook.useAudioTools>)

    vi.mocked(toolsHook.useAudioToolJobs).mockReturnValue({
      data: mockJobs,
      isLoading: false,
    } as unknown as ReturnType<typeof toolsHook.useAudioToolJobs>)

    render(
      <MemoryRouter>
        <AudioToolsHub />
      </MemoryRouter>
    )

    // Checks header
    expect(screen.getByText('Nền tảng Công cụ Âm thanh (Audio Tools Hub)')).toBeInTheDocument()

    // Checks tools rendered
    expect(screen.getAllByText('Cắt Audio chính xác').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Tách lời & beat AI')).toBeInTheDocument()
    expect(screen.getByText('Miễn phí')).toBeInTheDocument()
    expect(screen.getByText('2 cr/phút')).toBeInTheDocument()

    // Search filter
    const searchInput = screen.getByPlaceholderText(/Tìm kiếm công cụ/i)
    fireEvent.change(searchInput, { target: { value: 'Tách' } })

    expect(screen.queryByRole('heading', { name: 'Cắt Audio chính xác' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tách lời & beat AI' })).toBeInTheDocument()

    // Checks recent jobs rendered
    expect(screen.getByText(/speech.mp3/i)).toBeInTheDocument()
  })
})
