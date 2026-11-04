import { useEffect, useRef } from 'react'

interface Props {
  label: string
  value: number
  min: number
  max: number
  step: number
  displayValue: string
  scaleLabels: [string, string, string]
  onChange: (v: number) => void
}

export default function SliderControl({ label, value, min, max, step, displayValue, scaleLabels, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (inputRef.current) {
      const pct = ((value - min) / (max - min)) * 100
      inputRef.current.style.setProperty('--val', `${pct}%`)
    }
  }, [value, min, max])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-white/70">{label}</span>
        <span className="text-xs font-mono text-brand-400">{displayValue}</span>
      </div>
      <input
        ref={inputRef}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(parseInt(e.target.value, 10))}
        className="w-full"
      />
      <div className="flex justify-between text-[10px] text-white/25">
        <span>{scaleLabels[0]}</span>
        <span>{scaleLabels[1]}</span>
        <span>{scaleLabels[2]}</span>
      </div>
    </div>
  )
}
