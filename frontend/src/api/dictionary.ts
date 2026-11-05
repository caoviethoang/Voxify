import client from './client'

export interface DictionaryRule {
  id: number
  user_id: number
  word: string
  replacement: string
  category: 'abbreviation' | 'date' | 'number' | 'name' | 'custom'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateDictionaryRuleData {
  word: string
  replacement: string
  category?: string
}

export interface UpdateDictionaryRuleData {
  replacement?: string
  category?: string
  is_active?: boolean
}

/** Lấy danh sách quy tắc phát âm cá nhân */
export async function listDictionaryRules(): Promise<DictionaryRule[]> {
  const { data } = await client.get<DictionaryRule[]>('/dictionary')
  return data
}

/** Tạo quy tắc phát âm mới */
export async function createDictionaryRule(rule: CreateDictionaryRuleData): Promise<DictionaryRule> {
  const { data } = await client.post<DictionaryRule>('/dictionary', rule)
  return data
}

/** Cập nhật quy tắc phát âm */
export async function updateDictionaryRule(
  id: number,
  rule: UpdateDictionaryRuleData
): Promise<DictionaryRule> {
  const { data } = await client.put<DictionaryRule>(`/dictionary/${id}`, rule)
  return data
}

/** Xóa quy tắc phát âm */
export async function deleteDictionaryRule(id: number): Promise<void> {
  await client.delete(`/dictionary/${id}`)
}
