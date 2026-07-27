import { test, expect } from '@playwright/test';

test.describe('Verify Email endpoint tightening', () => {
  test.beforeEach(async ({ page }) => {
    // Mock English language
    await page.addInitScript(() => {
      window.localStorage.setItem('app_language', 'en');
    });
  });

  test('User receives rate limited error on verify email', async ({ page }) => {
    // Mock the API response to simulate rate limiting
    await page.route('**/auth/verify-email', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.verify_email_rate_limited' }),
      });
    });

    await page.goto('/verify-email?token=some_token');
    
    // Click verify
    await page.click('button:has-text("Verify email")');
    
    // Verify the correct translated text appears
    await expect(page.locator('text=Too many verification attempts. Please wait a moment.')).toBeVisible({ timeout: 5000 });
  });

  test('User receives invalid token error explicitly mapped', async ({ page }) => {
    // Mock the API response to simulate invalid token
    await page.route('**/auth/verify-email', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.verify_email_token_invalid_or_expired' }),
      });
    });

    await page.goto('/verify-email?token=invalid_token');
    
    // Click verify
    await page.click('button:has-text("Verify email")');
    
    // Verify the correct translated text appears
    await expect(page.locator('text=Invalid or expired verification link.')).toBeVisible({ timeout: 5000 });
  });
});
