import React from 'react'
import type { AudioToolParamsSchema } from '../../api/audio_tools'
import { RotateCcw } from 'lucide-react'

interface DynamicParamsFormProps {
  schema: AudioToolParamsSchema
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
  onReset?: () => void
  disabled?: boolean
}

export const DynamicParamsForm: React.FC<DynamicParamsFormProps> = ({
  schema,
  values,
  onChange,
  onReset,
  disabled = false,
}) => {
  const properties = schema?.properties || {}
  const keys = Object.keys(properties)

  if (keys.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-sm text-slate-500 dark:text-white/40 text-center">
        Công cụ này không yêu cầu tham số tùy chỉnh bổ sung.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/[0.08]">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <span>Tham số tùy chỉnh</span>
        </h3>
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            disabled={disabled}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 dark:text-white/40 dark:hover:text-indigo-400 transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Mặc định</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {keys.map((key) => {
          const prop = properties[key]
          const currentValue = values[key] !== undefined ? values[key] : prop.default
          const widget = prop['ui:widget']
          const isRequired = schema.required?.includes(key)

          // 1. SELECT WIDGET / ENUM
          if (widget === 'select' || (prop.enum && prop.enum.length > 0)) {
            const options = prop.enum || []
            const names = prop.enumNames || options.map(String)

            return (
              <div key={key} className="space-y-1.5 md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 dark:text-white/80">
                  {prop.title || key}
                  {isRequired && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                <select
                  value={String(currentValue ?? '')}
                  onChange={(e) => {
                    const val = prop.type === 'number' || prop.type === 'integer'
                      ? Number(e.target.value)
                      : e.target.value
                    onChange(key, val)
                  }}
                  disabled={disabled}
                  className="w-full bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-control px-3 py-2 text-xs text-slate-800 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
                >
                  {options.map((opt, idx) => (
                    <option key={String(opt)} value={String(opt)}>
                      {names[idx] !== undefined ? names[idx] : String(opt)}
                    </option>
                  ))}
                </select>
                {prop.description && (
                  <p className="text-[11px] text-slate-500 dark:text-white/40">
                    {prop.description}
                  </p>
                )}
              </div>
            )
          }

          // 2. SWITCH / BOOLEAN WIDGET
          if (widget === 'switch' || prop.type === 'boolean') {
            const isChecked = Boolean(currentValue)
            return (
              <div
                key={key}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] md:col-span-2"
              >
                <div>
                  <div className="text-xs font-medium text-slate-700 dark:text-white/80">
                    {prop.title || key}
                  </div>
                  {prop.description && (
                    <p className="text-[11px] text-slate-500 dark:text-white/40 mt-0.5">
                      {prop.description}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={isChecked}
                  disabled={disabled}
                  onClick={() => onChange(key, !isChecked)}
                  className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 disabled:opacity-50 ${
                    isChecked ? 'bg-indigo-600' : 'bg-slate-300 dark:bg-white/20'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      isChecked ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            )
          }

          // 3. SLIDER WIDGET (Range with live value)
          if (widget === 'slider' || (prop.type === 'number' && prop.minimum !== undefined && prop.maximum !== undefined)) {
            const min = prop.minimum ?? 0
            const max = prop.maximum ?? 100
            const step = prop.step ?? (prop.type === 'integer' ? 1 : 0.1)
            const numVal = typeof currentValue === 'number' ? currentValue : Number(currentValue ?? min)

            return (
              <div key={key} className="space-y-2 p-3 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] md:col-span-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-700 dark:text-white/80">
                    {prop.title || key}
                  </label>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 font-mono">
                    {numVal} {prop.unit || ''}
                  </span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={numVal}
                  disabled={disabled}
                  onChange={(e) => onChange(key, parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 dark:bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-600 disabled:opacity-50"
                />
                <div className="flex justify-between text-[10px] text-slate-400 dark:text-white/30 font-mono">
                  <span>{min} {prop.unit || ''}</span>
                  <span>{max} {prop.unit || ''}</span>
                </div>
                {prop.description && (
                  <p className="text-[11px] text-slate-500 dark:text-white/40 pt-1 border-t border-slate-100 dark:border-white/[0.04]">
                    {prop.description}
                  </p>
                )}
              </div>
            )
          }

          // 4. NUMBER INPUT
          if (prop.type === 'number' || prop.type === 'integer') {
            const numVal = currentValue !== undefined ? Number(currentValue) : ''
            return (
              <div key={key} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-medium text-slate-700 dark:text-white/80">
                    {prop.title || key}
                    {isRequired && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  {prop.unit && (
                    <span className="text-[11px] text-slate-400 dark:text-white/40 font-mono">
                      {prop.unit}
                    </span>
                  )}
                </div>
                <input
                  type="number"
                  min={prop.minimum}
                  max={prop.maximum}
                  step={prop.step || (prop.type === 'integer' ? 1 : 0.1)}
                  value={numVal}
                  disabled={disabled}
                  onChange={(e) => {
                    const parsed = e.target.value === '' ? '' : parseFloat(e.target.value)
                    onChange(key, parsed)
                  }}
                  className="w-full bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-control px-3 py-2 text-xs text-slate-800 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
                />
                {prop.description && (
                  <p className="text-[11px] text-slate-500 dark:text-white/40">
                    {prop.description}
                  </p>
                )}
              </div>
            )
          }

          // 5. DEFAULT STRING INPUT
          return (
            <div key={key} className="space-y-1.5 md:col-span-2">
              <label className="block text-xs font-medium text-slate-700 dark:text-white/80">
                {prop.title || key}
                {isRequired && <span className="text-red-500 ml-0.5">*</span>}
              </label>
              <input
                type="text"
                value={String(currentValue ?? '')}
                disabled={disabled}
                onChange={(e) => onChange(key, e.target.value)}
                className="w-full bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-control px-3 py-2 text-xs text-slate-800 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
              />
              {prop.description && (
                <p className="text-[11px] text-slate-500 dark:text-white/40">
                  {prop.description}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
