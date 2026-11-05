import { test, expect } from '@playwright/test'

test.describe('Authentication Flows', () => {
  test('should display login page elements properly', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/Voxify/i)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByPlaceholder(/email/i)).toBeVisible()
    await expect(page.getByPlaceholder(/mật khẩu/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /đăng nhập/i })).toBeVisible()
  })

  test('should show error when login fails', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email hoặc mật khẩu không chính xác' }),
      })
    })

    await page.goto('/login')
    await page.getByPlaceholder(/email/i).fill('invalid@example.com')
    await page.getByPlaceholder(/mật khẩu/i).fill('WrongPassword123!')
    await page.getByRole('button', { name: /đăng nhập/i }).click()

    await expect(page.getByText(/không chính xác/i)).toBeVisible()
  })

  test('should login successfully and redirect to dashboard, then logout', async ({ page }) => {
    // Mock login endpoint
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake-jwt-token-12345',
          refresh_token: 'fake-refresh-token-12345',
          token_type: 'bearer',
          user: {
            id: 1,
            email: 'user@example.com',
            full_name: 'Việt Hoàng',
            role: 'user',
            credits: 2000,
          },
        }),
      })
    })

    // Mock me endpoint
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'user@example.com',
          full_name: 'Việt Hoàng',
          role: 'user',
          credits: 2000,
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
          credits_balance: 2000,
          recent_jobs: [],
        }),
      })
    })

    await page.goto('/login')
    await page.getByPlaceholder(/email/i).fill('user@example.com')
    await page.getByPlaceholder(/mật khẩu/i).fill('ValidPassword123!')
    await page.getByRole('button', { name: /đăng nhập/i }).click()

    // Should redirect to dashboard or studio
    await page.waitForURL((url) => url.pathname.includes('/dashboard') || url.pathname.includes('/studio'))
    expect(page.url()).not.toContain('/login')

    // Logout
    const logoutBtn = page.getByRole('button', { name: /đăng xuất/i })
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
      await expect(page).toHaveURL(/.*login/)
    }
  })
})

