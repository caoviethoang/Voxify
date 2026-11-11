import React from 'react'
import {
  Scissors,
  Volume2,
  FileAudio,
  Gauge,
  Sparkles,
  Music,
  Mic,
  Sliders,
  Settings,
  AudioWaveform,
  Waves,
} from 'lucide-react'

interface ToolIconProps {
  name: string
  className?: string
}

export const ToolIcon: React.FC<ToolIconProps> = ({ name, className = 'w-5 h-5' }) => {
  const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    scissors: Scissors,
    trim: Scissors,
    cut: Scissors,
    volume: Volume2,
    volume2: Volume2,
    fileaudio: FileAudio,
    convert: FileAudio,
    gauge: Gauge,
    tempo: Gauge,
    speed: Gauge,
    sparkles: Sparkles,
    noise: Waves,
    music: Music,
    vocal: Music,
    mic: Mic,
    recorder: Mic,
    sliders: Sliders,
    waveform: AudioWaveform,
  }

  const normalized = name.toLowerCase().replace(/[-_]/g, '')
  const IconComponent = iconMap[normalized] || Settings

  return <IconComponent className={className} />
}
