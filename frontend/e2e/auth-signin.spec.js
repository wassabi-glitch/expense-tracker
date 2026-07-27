import { test, expect } from '@playwright/test';

test.describe('Sign In Form', () => {
  test('validates form fields and displays backend errors correctly', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('app_language', 'en');
    });

    await page.goto('/sign-in');

    // Type invalid email and short password — mode="onChange" validates as you type
    await page.locator('#email').fill('invalid-email');
    await page.locator('#password').fill('short');
    // Press Enter to trigger submission attempt
    await page.locator('#password').press('Enter');

    // Validation messages are translated:
    // "auth.validation.email.invalid" → "Enter a valid email address"
    // "auth.validation.password.loginMin" → "Password too short (min 6)"
    await expect(page.getByText('Enter a valid email address')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Password too short (min 6)')).toBeVisible({ timeout: 5000 });

    // Fix the values
    await page.locator('#email').fill('valid@example.com');
    await page.locator('#password').fill('ValidPassword1!');
    await expect(page.getByText('Enter a valid email address')).toBeHidden({ timeout: 5000 });

    // Mock sign-in to return invalid credentials
    await page.route('**/users/sign-in', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'auth.invalid_credentials' }),
      });
    });

    await page.locator('button[type="submit"]').click();

    // "auth.invalidCredentials" → "Invalid email or password."
    // Can appear in multiple places (email error, password error, form status).
    // Use .first() to avoid strict mode violation.
    await expect(page.getByText('Invalid email or password.').first()).toBeVisible({ timeout: 10000 });
  });
});
