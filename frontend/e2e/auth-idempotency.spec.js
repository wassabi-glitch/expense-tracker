import { test, expect } from '@playwright/test';

test('User receives idempotency conflict on signup', async ({ page }) => {
  // Mock English language
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  // Mock the API response to simulate idempotency conflict
  await page.route('**/users/sign-up', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.idempotency_conflict_in_progress' }),
    });
  });

  await page.goto('/sign-up');
  
  const randomSuffix = Math.floor(Math.random() * 1000000);
  await page.fill('#signup-email', `idem_${randomSuffix}@example.com`);
  await page.fill('#signup-username-step', `idem_${randomSuffix}`);
  
  await page.click('button[type="button"]'); // Continue button
  
  // Wait for the password step
  const passwordInput = page.locator('#password');
  await passwordInput.waitFor({ state: 'visible' });
  await passwordInput.fill('StrongPassword123!');
  
  // Click Create Account
  await page.click('button[type="submit"]');

  // Verify the correct translated text appears
  await expect(page.locator('text=Sign-up is already in progress. Please wait a moment.')).toBeVisible({ timeout: 5000 });
});
