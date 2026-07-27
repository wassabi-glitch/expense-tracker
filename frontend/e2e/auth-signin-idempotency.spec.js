import { test, expect } from '@playwright/test';

test('User hits idempotency conflict on login', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  await page.route('**/users/sign-in', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.idempotency_conflict_in_progress' }),
    });
  });

  await page.goto('/sign-in');
  
  await page.fill('input[type="email"]', 'idempotency@example.com');
  await page.fill('input[type="password"]', 'Password123!');
  
  await page.click('button[type="submit"]');

  await expect(page.locator('text=Sign-in is already in progress. Please wait a moment.')).toBeVisible({ timeout: 5000 });
});
