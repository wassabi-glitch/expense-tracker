import { test, expect } from "@playwright/test";

test.describe("Layout Responsive & Routing", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a page that uses Layout. Wait for networkidle if needed, or DOM load.
    await page.goto("/dashboard");
    
    // We assume the user is logged in via state injection or we just test the layout rendering if the app handles unauthenticated redirects by mocking API, but since this is an E2E test, we should mock the API route to return a fake user, otherwise it redirects to /sign-in.
    await page.route("**/api/v1/auth/me", async (route) => {
      const json = { id: 1, email: "test@example.com", username: "testuser" };
      await route.fulfill({ json });
    });
    
    // Also mock wallets/expenses/etc if they are loaded on /dashboard to prevent crashing
    await page.route("**/api/v1/wallets**", async (route) => {
      await route.fulfill({ json: [] });
    });
    
    // Reload with mocks
    await page.goto("/dashboard");
  });

  test("Desktop (lg) layout displays expanded sidebar", async ({ page }) => {
    // Set viewport to lg (e.g. 1280x800)
    await page.setViewportSize({ width: 1280, height: 800 });

    // The layout has a sidebar element. Let's check for navigation labels being visible.
    const dashboardLink = page.locator('a[href="/dashboard"]').first();
    await expect(dashboardLink).toBeVisible();

    // Verify the label text is visible inside the link
    // Wait for translations to load if necessary, but we can just check if the text exists.
    // In English, it should say "Dashboard"
    await expect(dashboardLink).toContainText("Dashboard");
  });

  test("Tablet (md) layout displays unpinned icon-only sidebar", async ({ page }) => {
    // Set viewport to md (e.g. 768x1024)
    await page.setViewportSize({ width: 800, height: 1024 });

    // In tablet mode, the sidebar is visible, but text should be hidden (max-w-0 opacity-0)
    const dashboardLink = page.locator('a[href="/dashboard"]').first();
    await expect(dashboardLink).toBeVisible();

    // The text span is hidden by max-width: 0 and opacity: 0
    // Playwright `toBeVisible()` checks if bounding box is non-empty. 
    // We can assert the class or check that the span inside the link is not visible
    const textSpan = dashboardLink.locator('span:last-child');
    // It has `max-w-0 opacity-0` which might technically still exist in DOM.
    // Let's just check the sidebar's width or the link's width
    const box = await dashboardLink.boundingBox();
    // Icon wrapper is 40px wide. With padding, the row is roughly 40-50px wide in compact mode.
    expect(box.width).toBeLessThan(100); 
  });

  test("Navigation routing updates the URL and content", async ({ page }) => {
    // Navigate to Wallets
    const walletsLink = page.locator('a[href="/wallets"]').first();
    await walletsLink.click();
    
    await expect(page).toHaveURL(/.*\/wallets/);
  });
});
