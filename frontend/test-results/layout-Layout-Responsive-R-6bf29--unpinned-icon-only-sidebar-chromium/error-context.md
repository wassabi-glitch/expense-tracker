# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: layout.spec.js >> Layout Responsive & Routing >> Tablet (md) layout displays unpinned icon-only sidebar
- Location: e2e\layout.spec.js:37:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('a[href="/dashboard"]').first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('a[href="/dashboard"]').first()

```

```yaml
- text: "[plugin:vite:import-analysis] Failed to resolve import \"react-icons/io5\" from \"src/components/Layout.jsx\". Does the file exist? D:/Projects/ExpenseTracker/frontend/src/components/Layout.jsx:46:7 46 | IoDownloadOutline, 47 | IoSettingsOutline 48 | } from \"react-icons/io5\"; | ^ 49 | import { cn } from \"@/lib/utils\"; 50 | import { getCurrentUser, logout } from \"@/lib/api\"; at TransformPluginContext._formatLog (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:29079:43) at TransformPluginContext.error (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:29076:14) at normalizeUrl (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:27199:18) at process.processTicksAndRejections (node:internal/process/task_queues:103:5) at async file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:27257:32 at async Promise.all (index 10) at async TransformPluginContext.transform (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:27225:4) at async EnvironmentPluginContainer.transform (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:28877:14) at async loadAndTransform (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:22746:26) at async viteTransformMiddleware (file:///D:/Projects/ExpenseTracker/frontend/node_modules/vite/dist/node/chunks/config.js:24622:20) Click outside, press Esc key, or fix the code to dismiss. You can also disable this overlay by setting"
- code: server.hmr.overlay
- text: to
- code: "false"
- text: in
- code: vite.config.js
- text: .
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | 
  3  | test.describe("Layout Responsive & Routing", () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     // Navigate to a page that uses Layout. Wait for networkidle if needed, or DOM load.
  6  |     await page.goto("/dashboard");
  7  | 
  8  |     // We assume the user is logged in via state injection or we just test the layout rendering if the app handles unauthenticated redirects by mocking API, but since this is an E2E test, we should mock the API route to return a fake user, otherwise it redirects to /sign-in.
  9  |     await page.route("**/api/v1/users/me", async (route) => {
  10 |       const json = { id: 1, email: "test@example.com", username: "testuser" };
  11 |       await route.fulfill({ json });
  12 |     });
  13 | 
  14 |     // Also mock wallets/expenses/etc if they are loaded on /dashboard to prevent crashing
  15 |     await page.route("**/api/v1/wallets**", async (route) => {
  16 |       await route.fulfill({ json: [] });
  17 |     });
  18 | 
  19 |     // Reload with mocks
  20 |     await page.goto("/dashboard");
  21 |   });
  22 | 
  23 |   test("Desktop (lg) layout displays expanded sidebar", async ({ page }) => {
  24 |     // Set viewport to lg (e.g. 1280x800)
  25 |     await page.setViewportSize({ width: 1280, height: 800 });
  26 | 
  27 |     // The layout has a sidebar element. Let's check for navigation labels being visible.
  28 |     const dashboardLink = page.locator('a[href="/dashboard"]').first();
  29 |     await expect(dashboardLink).toBeVisible();
  30 | 
  31 |     // Verify the label text is visible inside the link
  32 |     // Wait for translations to load if necessary, but we can just check if the text exists.
  33 |     // In English, it should say "Dashboard"
  34 |     await expect(dashboardLink).toContainText("Dashboard");
  35 |   });
  36 | 
  37 |   test("Tablet (md) layout displays unpinned icon-only sidebar", async ({ page }) => {
  38 |     // Set viewport to md (e.g. 768x1024)
  39 |     await page.setViewportSize({ width: 800, height: 1024 });
  40 | 
  41 |     // In tablet mode, the sidebar is visible, but text should be hidden (max-w-0 opacity-0)
  42 |     const dashboardLink = page.locator('a[href="/dashboard"]').first();
> 43 |     await expect(dashboardLink).toBeVisible();
     |                                 ^ Error: expect(locator).toBeVisible() failed
  44 | 
  45 |     // The text span is hidden by max-width: 0 and opacity: 0
  46 |     // Playwright `toBeVisible()` checks if bounding box is non-empty. 
  47 |     // We can assert the class or check that the span inside the link is not visible
  48 |     const textSpan = dashboardLink.locator('span:last-child');
  49 |     // It has `max-w-0 opacity-0` which might technically still exist in DOM.
  50 |     // Let's just check the sidebar's width or the link's width
  51 |     const box = await dashboardLink.boundingBox();
  52 |     // Icon wrapper is 40px wide. With padding, the row is roughly 40-50px wide in compact mode.
  53 |     expect(box.width).toBeLessThan(100);
  54 |   });
  55 | 
  56 |   test("Navigation routing updates the URL and content", async ({ page }) => {
  57 |     // Navigate to Wallets
  58 |     const walletsLink = page.locator('a[href="/wallets"]').first();
  59 |     await walletsLink.click();
  60 | 
  61 |     await expect(page).toHaveURL(/.*\/wallets/);
  62 |   });
  63 | });
  64 | 
```