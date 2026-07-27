import { test, expect } from '@playwright/test';

test('User hits idempotency conflict on forgot password', async ({ page }) => {
  // Force English
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  await page.goto('/forgot-password');

  // Mock the API to simulate idempotency conflict
  await page.route('**/auth/forgot-password', async route => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.idempotency_conflict_in_progress' }),
    });
  });

  // Fill in email and submit
  await page.fill('#email', 'idempotency@example.com');
  await page.click('button[type="submit"]');

  // Verify the error message — the mapForgotError function calls
  // t("auth.idempotencyConflict") which renders the translated text
  await expect(page.locator('text=Request is already in progress. Please wait a moment.')).toBeVisible();
});

test('User hits idempotency conflict on reset password', async ({ page }) => {
  // Force English
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  await page.goto('/reset-password?token=valid_token');

  // Mock the API to simulate idempotency conflict
  await page.route('**/auth/reset-password', async route => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.idempotency_conflict_in_progress' }),
    });
  });

  // Fill in new password
  await page.fill('#new_password', 'StrongPassword123!');
  await page.fill('#confirm_password', 'StrongPassword123!');

  // Submit
  await page.click('button[type="submit"]');

  // Verify the idempotency error message
  await expect(page.locator('text=Request is already in progress. Please wait a moment.')).toBeVisible();
});
