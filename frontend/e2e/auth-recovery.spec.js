import { test, expect } from '@playwright/test';

test.describe('Auth Recovery flows (Forgot & Reset Password)', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('app_language', 'en');
    });
  });

  test('User receives rate limited error on forgot password', async ({ page }) => {
    await page.route('**/auth/forgot-password', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.forgot_password_rate_limited' }),
      });
    });

    await page.goto('/forgot-password');

    await page.fill('#email', 'test@example.com');
    await page.click('button:has-text("Send reset link")');

    await expect(page.locator('text=Too many password reset requests. Please try again later.')).toBeVisible({ timeout: 5000 });
  });

  test('User receives invalid token error on reset password', async ({ page }) => {
    await page.route('**/auth/reset-password', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.reset_token_invalid_or_expired' }),
      });
    });

    await page.goto('/reset-password?token=invalid_token');

    await page.fill('#new_password', 'ValidPass123!');
    await page.fill('#confirm_password', 'ValidPass123!');

    await page.click('button:has-text("Save password")');

    await expect(page.locator('text=Invalid or expired reset token')).toBeVisible({ timeout: 5000 });
  });

  test('User receives rate limited error on reset password', async ({ page }) => {
    await page.route('**/auth/reset-password', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.reset_password_rate_limited' }),
      });
    });

    await page.goto('/reset-password?token=some_token');

    await page.fill('#new_password', 'ValidPass123!');
    await page.fill('#confirm_password', 'ValidPass123!');

    await page.click('button:has-text("Save password")');

    await expect(page.locator('text=Too many password reset attempts. Please try again later.')).toBeVisible({ timeout: 5000 });
  });
});
