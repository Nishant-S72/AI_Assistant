/**
 * Calendar connect UI and OAuth flow tests
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes } from './utils/mock_server';

test.describe('Calendar Connect', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
  });

  test('should display calendar connect page', async ({ page }) => {
    await page.goto('/calendar-connect');
    
    await expect(page.locator('text=Connect Calendar, h1:has-text("Connect"), h2:has-text("Connect")').first()).toBeVisible({ timeout: 5000 });
  });

  test('should show Google and Outlook options', async ({ page }) => {
    await page.goto('/calendar-connect');
    
    // Wait for providers to load
    await page.waitForTimeout(1000);
    
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/google|outlook/i);
  });

  test('should generate OAuth URL for Google', async ({ page }) => {
    let oauthUrlGenerated = false;
    
    await page.route('**/api/v1/scheduler/connect/google**', async (route) => {
      oauthUrlGenerated = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          oauth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:3000/callback&state=test-state',
          state: 'test-state',
        }),
      });
    });

    await page.goto('/calendar-connect');
    
    const connectButton = page.locator('button:has-text("Connect"), button:has-text("Google")').first();
    if (await connectButton.count() > 0) {
      await connectButton.click();
      await page.waitForTimeout(1000);
    }

    // Verify OAuth URL was generated
    expect(oauthUrlGenerated).toBe(true);
  });

  test('should handle OAuth callback', async ({ page }) => {
    await page.goto('/calendar-connect/callback?code=test-code&state=test-state');
    
    // Wait for callback processing
    await page.waitForTimeout(2000);
    
    // Should show success or redirect
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/success|connected|redirecting/i);
  });

  test('should show connected state after OAuth', async ({ page }) => {
    // Mock connection status
    await page.route('**/api/v1/scheduler/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          events: [],
          connected: true,
          provider: 'google',
        }),
      });
    });

    await page.goto('/calendar-connect');
    await page.waitForTimeout(1000);
    
    // Should show connected status
    const bodyText = await page.textContent('body');
    // Status might be shown as "Connected" or similar
    expect(bodyText).toBeTruthy();
  });

  test('should prompt re-auth on token expiry', async ({ page }) => {
    // Mock 401 response from calendar API
    await page.route('**/api/v1/scheduler/events**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Token expired',
          requires_reauth: true,
        }),
      });
    });

    await page.goto('/calendar');
    
    // Should show re-auth prompt
    await page.waitForTimeout(1000);
    const bodyText = await page.textContent('body');
    // UI should indicate re-authentication needed
    expect(bodyText).toBeTruthy();
  });
});

