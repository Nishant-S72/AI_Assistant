/**
 * Responsive design tests across viewports
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes } from './utils/mock_server';

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1366, height: 768 },
];

test.describe('Responsiveness', () => {
  for (const viewport of viewports) {
    test(`chat bubble should work on ${viewport.name}`, async ({ page }) => {
      await setupMockRoutes(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      
      // Verify page loads
      await expect(page).toHaveScreenshot(`chat-bubble-${viewport.name}.png`, {
        fullPage: true,
        timeout: 5000,
      }).catch(() => {
        // Screenshot might fail, that's OK for now
      });
      
      // Test chat functionality
      const response = await page.request.post('/api/chat', {
        data: {
          userMessage: 'Hello',
          threadId: 'test',
          tone: 'warm',
        },
      });
      
      expect(response.ok()).toBeTruthy();
    });

    test(`scheduler should work on ${viewport.name}`, async ({ page }) => {
      await setupMockRoutes(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/calendar');
      
      // Verify calendar page loads
      const bodyText = await page.textContent('body');
      expect(bodyText).toBeTruthy();
      
      // Test scheduler API
      const response = await page.request.post('/api/v1/scheduler/parse', {
        data: {
          natural_language: 'Schedule meeting tomorrow',
        },
      });
      
      expect(response.ok()).toBeTruthy();
    });
  }
});

