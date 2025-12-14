/**
 * Visual regression tests
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes } from './utils/mock_server';

test.describe('Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
  });

  test('home page visual snapshot', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('home-page.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('calendar page visual snapshot', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('calendar-page.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('calendar connect page visual snapshot', async ({ page }) => {
    await page.goto('/calendar-connect');
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('calendar-connect-page.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('scheduler modal visual snapshot', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    // Try to open modal
    const schedulerButton = page.locator('[data-testid="open-scheduler"], button:has-text("Schedule")').first();
    if (await schedulerButton.count() > 0) {
      await schedulerButton.click();
      await page.waitForTimeout(1000);
      
      const modal = page.locator('[role="dialog"], [data-testid="scheduler-modal"]').first();
      if (await modal.count() > 0) {
        await expect(modal).toHaveScreenshot('scheduler-modal.png', {
          maxDiffPixels: 100,
        });
      }
    }
  });
});

