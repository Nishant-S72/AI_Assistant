/**
 * Accessibility tests using axe-core
 */
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { setupMockRoutes } from './utils/mock_server';

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
  });

  test('home page should be accessible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    // Save report
    const fs = require('fs');
    const path = require('path');
    const reportDir = path.join(__dirname, 'artifacts', 'accessibility');
    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }
    fs.writeFileSync(
      path.join(reportDir, 'home-page-a11y.json'),
      JSON.stringify(accessibilityScanResults, null, 2)
    );
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('calendar page should be accessible', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    const fs = require('fs');
    const path = require('path');
    const reportDir = path.join(__dirname, 'artifacts', 'accessibility');
    fs.writeFileSync(
      path.join(reportDir, 'calendar-page-a11y.json'),
      JSON.stringify(accessibilityScanResults, null, 2)
    );
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('calendar connect page should be accessible', async ({ page }) => {
    await page.goto('/calendar-connect');
    await page.waitForLoadState('networkidle');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    const fs = require('fs');
    const path = require('path');
    const reportDir = path.join(__dirname, 'artifacts', 'accessibility');
    fs.writeFileSync(
      path.join(reportDir, 'calendar-connect-a11y.json'),
      JSON.stringify(accessibilityScanResults, null, 2)
    );
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('scheduler modal should be accessible', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    // Try to open scheduler modal if button exists
    const schedulerButton = page.locator('[data-testid="open-scheduler"], button:has-text("Schedule")').first();
    if (await schedulerButton.count() > 0) {
      await schedulerButton.click();
      await page.waitForTimeout(500);
      
      const modal = page.locator('[role="dialog"], [data-testid="scheduler-modal"]').first();
      if (await modal.count() > 0) {
        const accessibilityScanResults = await new AxeBuilder({ page })
          .include(modal)
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze();
        
        const fs = require('fs');
        const path = require('path');
        const reportDir = path.join(__dirname, 'artifacts', 'accessibility');
        fs.writeFileSync(
          path.join(reportDir, 'scheduler-modal-a11y.json'),
          JSON.stringify(accessibilityScanResults, null, 2)
        );
        
        expect(accessibilityScanResults.violations).toEqual([]);
      }
    }
  });
});

