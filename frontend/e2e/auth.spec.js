import { test, expect } from '@playwright/test';

test('User can sign up and verify email', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  const email = `testuser_${Date.now()}@example.com`;
  const password = 'StrongPassword123!';

  // Mock signup
  await page.route('**/users/sign-up', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ verification_email_sent: true, email }),
    });
  });

  // Mock verify — the actual endpoint is POST /auth/verify-email
  await page.route('**/auth/verify-email', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Email verified successfully' }),
    });
  });

  // 1. Sign up
  await page.goto('/sign-up');
  await page.fill('#signup-email', email);
  await page.fill('#signup-username-step', email.split('@')[0]);
  await page.click('button:has-text("Continue")');

  const passwordInput = page.locator('#password');
  await passwordInput.waitFor({ state: 'visible' });
  await passwordInput.fill(password);
  await page.click('button[type="submit"]');

  // 2. Should land on resend-verification
  await expect(page).toHaveURL(/.*resend-verification.*/, { timeout: 15000 });

  // 3. Navigate to verify with any token (the API is mocked)
  await page.goto('/verify-email?token=test-verify-token');
  await page.click('button[type="button"]');

  // 4. Success message should appear
  await expect(page.locator('text=Email verified successfully')).toBeVisible({ timeout: 10000 });
});
