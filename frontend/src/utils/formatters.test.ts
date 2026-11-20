import { describe, it, expect } from 'vitest'
import {
  formatDuration,
  formatTotalDuration,
  formatRelativeTime,
  formatDate,
} from './formatters'

describe('formatters utility', () => {
  describe('formatDuration', () => {
    it('formats seconds into m:ss with padMinutes=false', () => {
      expect(formatDuration(0)).toBe('0:00')
      expect(formatDuration(18.5)).toBe('0:18')
      expect(formatDuration(25)).toBe('0:25')
      expect(formatDuration(65)).toBe('1:05')
      expect(formatDuration(3600)).toBe('60:00')
    })

    it('formats seconds into mm:ss with padMinutes=true', () => {
      expect(formatDuration(0, true)).toBe('00:00')
      expect(formatDuration(35, true)).toBe('00:35')
      expect(formatDuration(120, true)).toBe('02:00')
    })

    it('handles negative or invalid values gracefully', () => {
      expect(formatDuration(-5)).toBe('0:00')
      expect(formatDuration(-5, true)).toBe('00:00')
      expect(formatDuration(NaN)).toBe('0:00')
    })
  })

  describe('formatTotalDuration', () => {
    it('formats seconds into human readable duration in Vietnamese', () => {
      expect(formatTotalDuration(0)).toBe('0 giây')
      expect(formatTotalDuration(45)).toBe('45 giây')
      expect(formatTotalDuration(360)).toBe('6 phút')
      expect(formatTotalDuration(90)).toBe('1 phút 30s')
      expect(formatTotalDuration(3665)).toBe('1 giờ 1 phút')
    })

    it('handles negative or NaN values', () => {
      expect(formatTotalDuration(-10)).toBe('0 giây')
      expect(formatTotalDuration(NaN)).toBe('0 giây')
    })
  })

  describe('formatRelativeTime', () => {
    it('returns empty string if date is missing or invalid', () => {
      expect(formatRelativeTime(undefined)).toBe('')
      expect(formatRelativeTime('invalid-date')).toBe('')
    })

    it('formats recent timestamps', () => {
      const now = new Date()
      expect(formatRelativeTime(now.toISOString())).toBe('vừa xong')

      const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000)
      expect(formatRelativeTime(twoMinutesAgo.toISOString())).toBe('2 phút trước')

      const threeHoursAgo = new Date(Date.now() - 3 * 3600 * 1000)
      expect(formatRelativeTime(threeHoursAgo.toISOString())).toBe('3 giờ trước')

      const fourDaysAgo = new Date(Date.now() - 4 * 24 * 3600 * 1000)
      expect(formatRelativeTime(fourDaysAgo.toISOString())).toBe('4 ngày trước')
    })
  })

  describe('formatDate', () => {
    it('returns empty string on empty or invalid input', () => {
      expect(formatDate(undefined)).toBe('')
      expect(formatDate('')).toBe('')
      expect(formatDate('invalid-date')).toBe('')
    })

    it('formats date string correctly with and without time', () => {
      const dateStr = '2026-02-01T08:30:00.000Z'
      const formattedWithTime = formatDate(dateStr)
      expect(formattedWithTime).toContain('2026')

      const formattedDateOnly = formatDate(dateStr, false)
      expect(formattedDateOnly).toContain('2026')
    })
  })
})
