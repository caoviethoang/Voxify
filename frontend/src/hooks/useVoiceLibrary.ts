import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchVoiceLibrary,
  toggleVoiceFavorite,
  type FetchVoiceLibraryParams,
  type VoiceLibraryListResponse,
} from '../api/voice_library'

export function useVoiceLibrary(params?: FetchVoiceLibraryParams) {
  return useQuery<VoiceLibraryListResponse>({
    queryKey: ['voice-library', params],
    queryFn: () => fetchVoiceLibrary(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useToggleFavorite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (voiceId: number) => toggleVoiceFavorite(voiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-library'] })
      queryClient.invalidateQueries({ queryKey: ['voices'] })
    },
  })
}
