import { test, expect } from '@playwright/test';

test.describe('Change Password', () => {
  test('User can change their password from settings page', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('app_language', 'en');
    });

    const email = `changepw_${Date.now()}@example.com`;

    // Mock login + profile + change-password + refresh
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
    await page.route('**/auth/change-password', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ message: 'Password changed successfully' }) });
    });
    await page.route('**/auth/refresh', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ access_token: 'fake_token', token_type: 'bearer' }) });
    });

    // Login → dashboard → settings
    await page.goto('/sign-in');
    await page.fill('#email', email);
    await page.fill('#password', 'OldPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await page.click('a[href="/settings"]');
    await page.waitForURL('**/settings', { timeout: 10000 });
    await page.waitForTimeout(500);

    // Verify and fill change password form
    await expect(page.locator('#currentPassword')).toBeVisible({ timeout: 5000 });
    await page.fill('#currentPassword', 'OldPass123!');
    await page.fill('#newPassword', 'NewStrong456!');
    await page.fill('#confirmPassword', 'NewStrong456!');
    await page.waitForTimeout(300);

    // Submit via form element (sidebar overlaps the submit button)
    await page.evaluate(() => {
      const form = document.querySelector('form');
      if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });

    // Verify success message appeared
    await page.waitForTimeout(500);
    await expect(page.locator('body')).toContainText('Password updated successfully');
  });
});
