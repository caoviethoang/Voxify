import { describe, it, expect } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { extractApiErrorMessage } from './apiError'

const mockConfig = {} as InternalAxiosRequestConfig

describe('extractApiErrorMessage', () => {
  it('returns fallback message if error is undefined or null', () => {
    expect(extractApiErrorMessage(undefined, 'Fallback')).toBe('Fallback')
    expect(extractApiErrorMessage(null, 'Fallback')).toBe('Fallback')
  })

  it('extracts detail string from AxiosError', () => {
    const error = new AxiosError('Request failed')
    error.response = {
      data: { detail: 'Tài khoản đã bị khóa' },
      status: 403,
      statusText: 'Forbidden',
      headers: {},
      config: mockConfig,
    }
    expect(extractApiErrorMessage(error)).toBe('Tài khoản đã bị khóa')
  })

  it('extracts first msg from FastAPI validation array', () => {
    const error = new AxiosError('Unprocessable Entity')
    error.response = {
      data: {
        detail: [
          { loc: ['body', 'email'], msg: 'Email không hợp lệ', type: 'value_error' },
        ],
      },
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: mockConfig,
    }
    expect(extractApiErrorMessage(error)).toBe('Email không hợp lệ')
  })

  it('extracts nested error.message from AxiosError', () => {
    const error = new AxiosError('Server error')
    error.response = {
      data: { error: { message: 'Lỗi quota' } },
      status: 429,
      statusText: 'Too Many Requests',
      headers: {},
      config: mockConfig,
    }
    expect(extractApiErrorMessage(error)).toBe('Lỗi quota')
  })

  it('extracts direct string body from AxiosError', () => {
    const error = new AxiosError('Bad gateway')
    error.response = {
      data: 'Gateway timeout from upstream',
      status: 504,
      statusText: 'Gateway Timeout',
      headers: {},
      config: mockConfig,
    }
    expect(extractApiErrorMessage(error)).toBe('Gateway timeout from upstream')
  })

  it('extracts message from standard Error', () => {
    const error = new Error('Lỗi mạng nội bộ')
    expect(extractApiErrorMessage(error)).toBe('Lỗi mạng nội bộ')
  })

  it('returns raw string error if passed', () => {
    expect(extractApiErrorMessage('Lỗi từ chuỗi')).toBe('Lỗi từ chuỗi')
  })
})
