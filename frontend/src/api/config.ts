import client from './client'

export interface AppConfig {
  app_name: string
  max_chars: number
  max_text_length: number
  chunk_size: number
  default_voice: string
  tts_provider: string
}

export async function fetchConfig(): Promise<AppConfig> {
  const { data } = await client.get<AppConfig>('/config')
  return data
}
