import client from './client'

export type AudioToolCostType = 'free' | 'per_minute'

export interface JSONSchemaProperty {
  type?: 'string' | 'number' | 'integer' | 'boolean'
  title?: string
  description?: string
  default?: unknown
  minimum?: number
  maximum?: number
  step?: number
  unit?: string
  enum?: (string | number)[]
  enumNames?: string[]
  'ui:widget'?: 'slider' | 'select' | 'switch' | 'file' | 'textarea'
}

export interface AudioToolParamsSchema {
  type: 'object'
  properties: Record<string, JSONSchemaProperty>
  required?: string[]
}

export interface AudioTool {
  id: string
  name_vi: string
  name_en: string
  category: string
  icon: string
  cost_type: AudioToolCostType
  cost_credits: number
  heavy: boolean
  description_vi: string
  description_en: string
  params_schema: AudioToolParamsSchema
}

export interface CategoryMetadata {
  id: string
  title_vi: string
  title_en: string
  icon: string
  order: number
}

export interface AudioToolCategoryGroup {
  category: string
  meta: CategoryMetadata
  tools: AudioTool[]
}

export interface AudioToolListResponse {
  categories: AudioToolCategoryGroup[]
  total_tools: number
}

export type AudioToolJobStatus = 'queued' | 'processing' | 'done' | 'failed'

export interface AudioToolJob {
  id: string
  user_id: number
  tool_id: string
  tool_name_vi?: string | null
  status: AudioToolJobStatus
  progress: number
  input_filename?: string | null
  input_duration?: number | null
  output_duration?: number | null
  output_format?: string | null
  credit_used: number
  error_message?: string | null
  created_at: string
  updated_at: string
  stream_url: string
  download_url: string
  params?: Record<string, unknown> | null
}

export interface CreateToolJobParams {
  file?: File | null
  source_generation_id?: number | null
  source_tool_job_id?: string | null
  params?: Record<string, unknown>
}

export async function fetchAudioTools(): Promise<AudioToolListResponse> {
  const response = await client.get<AudioToolListResponse>('/tools')
  return response.data
}

export async function fetchAudioTool(toolId: string): Promise<AudioTool> {
  const response = await client.get<AudioTool>(`/tools/${toolId}`)
  return response.data
}

export async function createAudioToolJob(
  toolId: string,
  payload: CreateToolJobParams
): Promise<AudioToolJob> {
  const formData = new FormData()

  if (payload.file) {
    formData.append('file', payload.file)
  }
  if (payload.source_generation_id) {
    formData.append('source_generation_id', String(payload.source_generation_id))
  }
  if (payload.source_tool_job_id) {
    formData.append('source_tool_job_id', payload.source_tool_job_id)
  }
  if (payload.params && Object.keys(payload.params).length > 0) {
    formData.append('params', JSON.stringify(payload.params))
  }

  const response = await client.post<AudioToolJob>(`/tools/${toolId}/jobs`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function fetchAudioToolJobs(toolId?: string): Promise<AudioToolJob[]> {
  const response = await client.get<AudioToolJob[]>('/tools/jobs', {
    params: toolId ? { tool_id: toolId } : undefined,
  })
  return response.data
}

export async function fetchAudioToolJob(jobId: string): Promise<AudioToolJob> {
  const response = await client.get<AudioToolJob>(`/tools/jobs/${jobId}`)
  return response.data
}
