import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DynamicParamsForm } from './DynamicParamsForm'
import type { AudioToolParamsSchema } from '../../api/audio_tools'

describe('DynamicParamsForm', () => {
  const schema: AudioToolParamsSchema = {
    type: 'object',
    properties: {
      speed: {
        type: 'number',
        title: 'Tốc độ',
        default: 1.0,
        minimum: 0.5,
        maximum: 2.0,
        step: 0.1,
        unit: 'x',
        'ui:widget': 'slider',
      },
      format: {
        type: 'string',
        title: 'Định dạng xuất',
        default: 'mp3',
        enum: ['mp3', 'wav', 'flac'],
        enumNames: ['MP3 Audio', 'WAV Lossless', 'FLAC Studio'],
        'ui:widget': 'select',
      },
      highpass: {
        type: 'boolean',
        title: 'Lọc thông cao',
        default: true,
        'ui:widget': 'switch',
      },
    },
    required: ['speed'],
  }

  it('renders slider, select, and switch controls properly', () => {
    const handleChange = vi.fn()
    const handleReset = vi.fn()

    render(
      <DynamicParamsForm
        schema={schema}
        values={{ speed: 1.2, format: 'mp3', highpass: true }}
        onChange={handleChange}
        onReset={handleReset}
      />
    )

    // Check titles rendered
    expect(screen.getByText('Tốc độ')).toBeInTheDocument()
    expect(screen.getByText('Định dạng xuất')).toBeInTheDocument()
    expect(screen.getByText('Lọc thông cao')).toBeInTheDocument()

    // Check default button
    expect(screen.getByText('Mặc định')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Mặc định'))
    expect(handleReset).toHaveBeenCalledTimes(1)

    // Check select change
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'wav' } })
    expect(handleChange).toHaveBeenCalledWith('format', 'wav')
  })

  it('handles empty schema cleanly', () => {
    const emptySchema: AudioToolParamsSchema = {
      type: 'object',
      properties: {},
    }

    render(
      <DynamicParamsForm
        schema={emptySchema}
        values={{}}
        onChange={vi.fn()}
      />
    )

    expect(
      screen.getByText('Công cụ này không yêu cầu tham số tùy chỉnh bổ sung.')
    ).toBeInTheDocument()
  })
})
