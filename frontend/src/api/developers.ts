import client from './client'

export interface ApiKeyItem {
  id: number
  name: string
  key_prefix: string
  is_active: boolean
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

export interface ApiKeyCreated {
  id: number
  name: string
  key_prefix: string
  raw_key: string
  created_at: string
}

export interface ApiStatsDailyItem {
  date: string
  requests: number
  credits: number
}

export interface ApiStats {
  total_requests: number
  total_credits: number
  daily_usage: ApiStatsDailyItem[]
}

export const developersApi = {
  listKeys: async (): Promise<ApiKeyItem[]> => {
    const res = await client.get<ApiKeyItem[]>('/developers/keys')
    return res.data
  },

  createKey: async (name: string): Promise<ApiKeyCreated> => {
    const res = await client.post<ApiKeyCreated>('/developers/keys', { name })
    return res.data
  },

  revokeKey: async (id: number): Promise<{ message: string }> => {
    const res = await client.delete<{ message: string }>(`/developers/keys/${id}`)
    return res.data
  },

  getStats: async (days: number = 7): Promise<ApiStats> => {
    const res = await client.get<ApiStats>('/developers/stats', {
      params: { days },
    })
    return res.data
  },
}
