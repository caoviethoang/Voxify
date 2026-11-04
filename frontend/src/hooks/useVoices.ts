import { useQuery } from '@tanstack/react-query'
import { fetchVoices } from '../api/tts'

export function useVoices() {
  return useQuery({
    queryKey: ['voices'],
    queryFn: fetchVoices,
    staleTime: 10 * 60 * 1000,
  })
}
