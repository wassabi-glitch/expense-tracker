import { test, expect } from '@playwright/test';

test('User receives error when using disposable email on signup', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  // Mock signup to return disposable email error
  await page.route('**/users/sign-up', async (route) => {
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.disposable_email_blocked' }),
    });
  });

  await page.goto('/sign-up');

  const randomSuffix = Math.floor(Math.random() * 1000000);
  await page.fill('#signup-email', `spammer_${randomSuffix}@mailinator.com`);
  await page.fill('#signup-username-step', `spammer_${randomSuffix}`);

  // Step 1: Click Continue
  await page.click('button:has-text("Continue")');

  // Step 2: Wait for password field
  const passwordInput = page.locator('#password');
  await passwordInput.waitFor({ state: 'visible' });
  await passwordInput.fill('StrongPassword123!');

  // Click Create Account — triggers the mocked API
  await page.click('button[type="submit"]');

  // The error text appears in TWO places: the email field error AND the form status.
  // Use .first() to avoid strict mode violation.
  await expect(page.locator('text=Registration with disposable email addresses is not allowed. Please use a real email.').first()).toBeVisible({ timeout: 5000 });
});
