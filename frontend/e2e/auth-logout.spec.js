import { test, expect } from '@playwright/test';

test.describe('Logout and Logout of All Devices', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('app_language', 'en');
    });
  });

  async function loginThenGoToSettings(page) {
    const email = `logout_${Date.now()}@example.com`;

    await page.route('**/users/sign-in', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake_token', token_type: 'bearer' }) });
    });
    await page.route('**/users/me', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ id: 1, email, username: email.split('@')[0],
          is_verified: true, is_premium: false, needs_onboarding: false,
          has_local_password: true, created_at: new Date().toISOString() }) });
    });
    await page.route('**/auth/refresh', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake_token', token_type: 'bearer' }) });
    });
    await page.route('**/auth/logout', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ message: 'Logged out' }) });
    });
    await page.route('**/auth/logout-all', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ message: 'Logged out of all devices' }) });
    });

    await page.goto('/sign-in');
    await page.fill('#email', email);
    await page.fill('#password', 'Pass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    await page.click('a[href="/settings"]');
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForTimeout(500);
  }

  test('User can log out from settings page', async ({ page }) => {
    await loginThenGoToSettings(page);

    // Click Sign Out button
    await page.click('button:has-text("Sign out")');
    // Confirm dialog — Dialog has two Sign out buttons (trigger + confirm)
    // Click the confirm one in the dialog
    await page.locator('[role="dialog"] button:has-text("Sign out")').click();

    // Should redirect to sign-in
    await expect(page).toHaveURL(/.*sign-in.*/, { timeout: 10000 });
  });

  test('User can log out of all devices from settings page', async ({ page }) => {
    await loginThenGoToSettings(page);

    // Click Logout of All Devices button
    await page.click('button:has-text("Logout of All Devices")');
    // Confirm dialog
    await page.locator('[role="dialog"] button:has-text("Logout of All Devices")').click();

    // Should redirect to sign-in
    await expect(page).toHaveURL(/.*sign-in.*/, { timeout: 10000 });
  });
});
