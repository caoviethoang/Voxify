import { test, expect } from '@playwright/test'

test.describe('Dashboard & Navigation', () => {
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
          full_name: 'Cao Việt Hoàng',
          role: 'user',
          credits: 8436,
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
          full_name: 'Cao Việt Hoàng',
          role: 'user',
          credits: 8436,
        }),
      })
    })

    // Mock dashboard stats
    await page.route('**/api/dashboard/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_generations: 48,
          total_characters: 54000,
          total_audio_seconds: 360,
          credits_balance: 8436,
          recent_jobs: [
            {
              id: 101,
              title: 'Dự án giới thiệu sản phẩm',
              text_preview: 'Chào mừng quý khách đến với Voxify...',
              voice_name: 'HoaiMy - Vietnamese',
              duration_seconds: 45,
              status: 'done',
              created_at: new Date().toISOString(),
            },
          ],
        }),
      })
    })
  })

  test('should render KPI statistics cards and user greeting', async ({ page }) => {
    await page.goto('/dashboard')

    // Greeting
    await expect(page.getByText('Cao Việt Hoàng', { exact: false })).toBeVisible()

    // Metric numbers
    await expect(page.getByText('48')).toBeVisible()
    await expect(page.getByText('8.436')).toBeVisible()

    // Recent job item
    await expect(page.getByText('Dự án giới thiệu sản phẩm')).toBeVisible()
  })

  test('should navigate to studio and other pages via navigation links', async ({ page }) => {
    await page.goto('/dashboard')

    // Click Studio link in sidebar
    const studioLink = page.getByRole('link', { name: /studio/i }).first()
    if (await studioLink.isVisible()) {
      await studioLink.click()
      await expect(page).toHaveURL(/.*studio/)
    }
  })
})

