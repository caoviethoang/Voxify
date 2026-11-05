import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import {
  type User,
  type LoginParams,
  type RegisterParams,
  apiLogin,
  apiRegister,
  apiGoogleLogin,
  apiGetMe,
  apiLogout,
} from '../api/auth'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (params: LoginParams) => Promise<void>
  register: (params: RegisterParams) => Promise<void>
  googleLogin: (credential: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  updateCredits: (newCredits: number) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const userData = await apiGetMe()
      setUser(userData)
    } catch {
      localStorage.removeItem('access_token')
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = async (params: LoginParams) => {
    const data = await apiLogin(params)
    localStorage.setItem('access_token', data.access_token)
    setUser(data.user)
  }

  const register = async (params: RegisterParams) => {
    await apiRegister(params)
    // Sau khi đăng ký, tự động đăng nhập
    await login({ email: params.email, password: params.password })
  }

  const googleLogin = async (credential: string) => {
    const data = await apiGoogleLogin(credential)
    localStorage.setItem('access_token', data.access_token)
    setUser(data.user)
  }

  const logout = async () => {
    try {
      await apiLogout()
    } catch {
      // Bỏ qua lỗi mạng khi logout
    } finally {
      localStorage.removeItem('access_token')
      setUser(null)
    }
  }

  const updateCredits = useCallback((newCredits: number) => {
    setUser((prev) => {
      if (!prev) return null
      if (prev.credits === newCredits) return prev
      return { ...prev, credits: newCredits }
    })
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        googleLogin,
        logout,
        refreshUser,
        updateCredits,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

