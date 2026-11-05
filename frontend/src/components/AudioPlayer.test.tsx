import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AudioPlayer from './AudioPlayer'

describe('AudioPlayer Component', () => {
  it('returns null when url is not provided', () => {
    const { container } = render(<AudioPlayer url={null} voiceName="HoaiMy" />)
    expect(container.firstChild).toBeNull()
  })

  it('renders voice name, format badge, and audio ready indicator', () => {
    render(
      <AudioPlayer
        url="http://test/audio.mp3"
        voiceName="HoaiMy - Vietnamese"
        format="mp3"
        duration={35}
      />
    )

    expect(screen.getByText('Audio sẵn sàng')).toBeInTheDocument()
    expect(screen.getByText('HoaiMy - Vietnamese')).toBeInTheDocument()
    expect(screen.getByText('mp3')).toBeInTheDocument()
    expect(screen.getByText('00:35')).toBeInTheDocument()
  })

  it('renders preview label when isPreview is true', () => {
    render(<AudioPlayer url="http://test/preview.mp3" voiceName="HoaiMy" isPreview={true} />)

    expect(screen.getByText('HoaiMy · [Nghe thử]')).toBeInTheDocument()
  })

  it('handles play and pause toggle', async () => {
    render(<AudioPlayer url="http://test/audio.mp3" voiceName="HoaiMy" duration={60} />)

    // Wait for auto-play on mount to resolve
    const pauseBtn = await screen.findByTitle('Tạm dừng')
    expect(pauseBtn).toBeInTheDocument()

    // Click to pause
    fireEvent.click(pauseBtn)
    expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalled()

    // Now it shows play button
    const playBtn = screen.getByTitle('Phát')
    expect(playBtn).toBeInTheDocument()

    // Click to play again
    fireEvent.click(playBtn)
    expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled()
  })

  it('cycles playback speed when speed button is clicked', () => {
    render(<AudioPlayer url="http://test/audio.mp3" voiceName="HoaiMy" duration={120} />)

    const speedBtn = screen.getByRole('button', { name: '1x' })
    expect(speedBtn).toBeInTheDocument()

    fireEvent.click(speedBtn)
    expect(screen.getByRole('button', { name: '1.25x' })).toBeInTheDocument()

    fireEvent.click(speedBtn)
    expect(screen.getByRole('button', { name: '1.5x' })).toBeInTheDocument()

    fireEvent.click(speedBtn)
    expect(screen.getByRole('button', { name: '2x' })).toBeInTheDocument()

    fireEvent.click(speedBtn)
    expect(screen.getByRole('button', { name: '1x' })).toBeInTheDocument()
  })

  it('renders SRT and VTT links when provided', () => {
    render(
      <AudioPlayer
        url="http://test/audio.mp3"
        voiceName="HoaiMy"
        srtUrl="http://test/subtitles.srt"
        vttUrl="http://test/subtitles.vtt"
      />
    )

    const srtLink = screen.getByTitle(/Tải phụ đề khớp thời gian chuẩn SRT/i)
    const vttLink = screen.getByTitle(/Tải phụ đề chuẩn WebVTT/i)

    expect(srtLink).toHaveAttribute('href', 'http://test/subtitles.srt')
    expect(vttLink).toHaveAttribute('href', 'http://test/subtitles.vtt')
  })

  it('invokes onDownload callback when download button is clicked', () => {
    const handleDownload = vi.fn()
    render(
      <AudioPlayer url="http://test/audio.mp3" voiceName="HoaiMy" onDownload={handleDownload} />
    )

    const downloadBtn = screen.getByRole('button', { name: /Tải MP3/i })
    fireEvent.click(downloadBtn)
    expect(handleDownload).toHaveBeenCalledTimes(1)
  })
})
