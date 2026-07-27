import { test, expect } from '@playwright/test';

test('User hits global rate limit on signup', async ({ page, request }) => {
  // 1. Force the rate limit by hitting the signup API directly many times
  // Assuming the limit is 100/min globally, we could hit it here, 
  // OR we can mock the API response if we use page.route
  
  // To avoid truly spamming the backend or dealing with dynamic limits,
  // the most reliable way to test frontend translation in E2E is mocking the network:
  // Force English language for deterministic text assertions
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  await page.route('**/users/sign-up', async (route) => {
    await route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.signup_global_rate_limited' }),
    });
  });

  // 2. Go to signup page
  await page.goto('/sign-up');
  
  // 3. Fill in details and submit
  const randomSuffix = Math.floor(Math.random() * 1000000);
  await page.fill('#signup-email', `testuser_${randomSuffix}@example.com`);
  await page.fill('#signup-username-step', `testuser_${randomSuffix}`);
  
  await page.click('button[type="button"]'); // Continue button
  
  // Wait for the password step
  const passwordInput = page.locator('#password');
  await passwordInput.waitFor({ state: 'visible' });
  await passwordInput.fill('StrongPassword123!');
  
  // Click Create Account
  await page.click('button[type="submit"]');

  // Verify the correct translated text appears
  await expect(page.locator('text=Too many sign-up attempts globally. Please try again later.')).toBeVisible({ timeout: 5000 });
});

test('User hits rate limit on login', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('app_language', 'en');
  });

  await page.route('**/users/sign-in', async (route) => {
    await route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'auth.login_rate_limited' }),
    });
  });

  await page.goto('/sign-in');
  
  await page.fill('input[type="email"]', 'ratelimited@example.com');
  await page.fill('input[type="password"]', 'WrongPassword123!');
  
  await page.click('button[type="submit"]');

  await expect(page.locator('text=Too many login attempts. Please try again later.')).toBeVisible({ timeout: 5000 });
});
