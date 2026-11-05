import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SliderControl from './SliderControl'

describe('SliderControl Component', () => {
  it('renders label and display value correctly', () => {
    const handleChange = vi.fn()
    render(
      <SliderControl
        label="Tốc độ"
        value={0}
        min={-50}
        max={100}
        step={5}
        displayValue="+0%"
        scaleLabels={['-50%', 'Mặc định', '+100%']}
        onChange={handleChange}
      />
    )

    expect(screen.getByText('Tốc độ')).toBeInTheDocument()
    expect(screen.getByText('+0%')).toBeInTheDocument()
    expect(screen.getByText('-50%')).toBeInTheDocument()
    expect(screen.getByText('Mặc định')).toBeInTheDocument()
    expect(screen.getByText('+100%')).toBeInTheDocument()
  })

  it('triggers onChange with parsed integer when input value changes', () => {
    const handleChange = vi.fn()
    render(
      <SliderControl
        label="Cao độ"
        value={0}
        min={-20}
        max={20}
        step={1}
        displayValue="0Hz"
        scaleLabels={['-20Hz', '0Hz', '+20Hz']}
        onChange={handleChange}
      />
    )

    const slider = screen.getByRole('slider')
    expect(slider).toHaveValue('0')

    fireEvent.change(slider, { target: { value: '10' } })
    expect(handleChange).toHaveBeenCalledWith(10)
  })

  it('respects min, max, and step attributes on input', () => {
    render(
      <SliderControl
        label="Âm lượng"
        value={50}
        min={0}
        max={100}
        step={10}
        displayValue="+50%"
        scaleLabels={['0%', '50%', '100%']}
        onChange={vi.fn()}
      />
    )

    const slider = screen.getByRole('slider')
    expect(slider).toHaveAttribute('min', '0')
    expect(slider).toHaveAttribute('max', '100')
    expect(slider).toHaveAttribute('step', '10')
  })
})
