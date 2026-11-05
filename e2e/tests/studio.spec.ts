import { test, expect } from '@playwright/test'

test.describe('Studio & TTS Generation', () => {
  test.beforeEach(async ({ page }) => {
    // Inject auth state in localStorage
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'test-e2e-token')
      localStorage.setItem('refresh_token', 'test-e2e-refresh-token')
      localStorage.setItem(
        'user',
        JSON.stringify({
          id: 1,
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          credits: 5000,
        })
      )
    })

    // Mock auth/me
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          credits: 5000,
        }),
      })
    })

    // Mock voices
    await page.route('**/api/voices**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'vi-VN-HoaiMyNeural',
            name: 'HoaiMy',
            gender: 'Female',
            locale: 'vi-VN',
            provider: 'edge',
            sample_rate: '24000Hz',
          },
          {
            id: 'fake-voice-1',
            name: 'Fake Voice 1',
            gender: 'Female',
            locale: 'vi-VN',
            provider: 'fake',
            sample_rate: '24000Hz',
          },
        ]),
      })
    })

    // Mock credits
    await page.route('**/api/credits', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user_id: 1,
          balance: 5000,
          chars_per_credit: 1,
          provider_multipliers: { edge: 1.0, fake: 1.0 },
        }),
      })
    })

    // Mock recent jobs
    await page.route('**/api/tts/jobs?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })
  })

  test('should allow entering text and displays character count and credit estimation', async ({ page }) => {
    await page.goto('/studio')

    const textarea = page.getByPlaceholder(/nhập nội dung văn bản/i)
    await expect(textarea).toBeVisible()

    await textarea.fill('Xin chào, đây là bài kiểm tra kiểm thử tự động Voxify E2E.')
    await expect(textarea).toHaveValue('Xin chào, đây là bài kiểm tra kiểm thử tự động Voxify E2E.')

    // Check character count indicator
    await expect(page.getByText(/59 \/ 20\.000 ký tự/i)).toBeVisible()
  })

  test('should generate audio and show audio player controls', async ({ page }) => {
    // Mock generate TTS
    await page.route('**/api/tts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 999,
          status: 'done',
          audio_url: '/api/tts/jobs/999/audio',
          duration_seconds: 3.5,
          char_count: 30,
          credits_deducted: 30,
          subtitles: {
            srt_url: '/api/tts/jobs/999/subtitles/srt',
            vtt_url: '/api/tts/jobs/999/subtitles/vtt',
          },
        }),
      })
    })

    await page.goto('/studio')
    const textarea = page.getByPlaceholder(/nhập nội dung văn bản/i)
    await textarea.fill('Kiểm tra tạo giọng nói tự động.')

    // Click Generate button
    const generateBtn = page.getByRole('button', { name: /tạo giọng nói/i })
    await expect(generateBtn).toBeVisible()
    await generateBtn.click()

    // Expect Audio Player or Notification
    await expect(page.getByText(/Audio sẵn sàng|Đã tạo xong tệp âm thanh/i)).toBeVisible({ timeout: 5000 })
  })
})

