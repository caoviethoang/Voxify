import client from './client'

export interface User {
  id: number
  email: string
  full_name?: string | null
  role: 'user' | 'admin'
  is_active: boolean
  is_verified: boolean
  credits: number
  credit_balance?: number
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RegisterParams {
  email: string
  password: string
  full_name?: string
}

export interface LoginParams {
  email: string
  password: string
}

export async function apiRegister(params: RegisterParams): Promise<User> {
  const { data } = await client.post<User>('/auth/register', params)
  return data
}

export async function apiLogin(params: LoginParams): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/login', params)
  return data
}

export async function apiGoogleLogin(credential: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/google', { credential })
  return data
}

export async function apiGetMe(): Promise<User> {
  const { data } = await client.get<User>('/auth/me')
  return data
}

export async function apiRefreshToken(): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/refresh')
  return data
}

export async function apiLogout(): Promise<void> {
  await client.post('/auth/logout')
}

export async function apiForgotPassword(email: string): Promise<{ message: string }> {
  const { data } = await client.post<{ message: string }>('/auth/forgot-password', { email })
  return data
}

export async function apiResetPassword(token: string, new_password: string): Promise<{ message: string }> {
  const { data } = await client.post<{ message: string }>('/auth/reset-password', { token, new_password })
  return data
}

export async function apiVerifyEmail(token: string): Promise<{ message: string }> {
  const { data } = await client.get<{ message: string }>(`/auth/verify-email?token=${encodeURIComponent(token)}`)
  return data
}
