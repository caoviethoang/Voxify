import { useQuery } from '@tanstack/react-query'
import { fetchConfig, type AppConfig } from '../api/config'

const DEFAULT_CONFIG: AppConfig = {
  app_name: 'Voxify',
  max_chars: 20000,
  max_text_length: 20000,
  chunk_size: 2500,
  default_voice: 'vi-VN-HoaiMyNeural',
  tts_provider: 'edge',
}

export function useAppConfig() {
  const { data, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: fetchConfig,
    staleTime: Infinity,
  })
  return { config: data ?? DEFAULT_CONFIG, isLoading }
}
