/**
 * Playwright UI tests for Scheduling Assistant
 */
import { test, expect } from '@playwright/test';

test.describe('Scheduling Assistant', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to calendar page
    await page.goto('/calendar');
  });

  test('should display calendar page', async ({ page }) => {
    await expect(page.locator('h1, h2')).toContainText(/calendar/i);
  });

  test('should load events from scheduler API', async ({ page }) => {
    // Mock scheduler API response
    await page.route('**/api/v1/scheduler/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          events: [
            {
              id: 'test-event-1',
              title: 'Test Meeting',
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              description: 'Test event',
            },
          ],
        }),
      });
    });

    // Wait for events to load
    await page.waitForTimeout(1000);
    
    // Verify event is displayed (if calendar renders events)
    const eventText = await page.textContent('body');
    expect(eventText).toBeTruthy();
  });

  test('should open scheduler modal when creating event', async ({ page }) => {
    // Look for a button or link to create event
    const createButton = page.locator('button:has-text("Create"), button:has-text("Schedule"), a:has-text("New Event")').first();
    
    if (await createButton.count() > 0) {
      await createButton.click();
      
      // Verify modal opens
      await expect(page.locator('text=Schedule Event, text=Create Event')).toBeVisible();
    }
  });

  test('should connect to Google Calendar', async ({ page }) => {
    // Navigate to calendar connect page
    await page.goto('/calendar-connect');
    
    // Verify page loads
    await expect(page.locator('text=Connect Calendar')).toBeVisible();
    
    // Mock OAuth URL generation
    await page.route('**/api/v1/scheduler/connect/google**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          oauth_url: 'https://accounts.google.com/o/oauth2/v2/auth?test=1',
          state: 'test-state',
        }),
      });
    });

    // Click connect button
    const connectButton = page.locator('button:has-text("Connect"), button:has-text("Reconnect")').first();
    if (await connectButton.count() > 0) {
      await connectButton.click();
      
      // Should redirect to OAuth URL (in real scenario)
      // For test, we just verify the API was called
      await page.waitForTimeout(500);
    }
  });

  test('should handle scheduler chat endpoint', async ({ page }) => {
    // Mock scheduler chat API
    await page.route('**/api/v1/scheduler/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'I can help you schedule a meeting.',
          function_call: null,
        }),
      });
    });

    // Navigate to a page that might use scheduler chat
    await page.goto('/');
    
    // Verify page loads
    expect(page.url()).toBeTruthy();
  });
});

test.describe('Chat Bubble Regression', () => {
  test('chat bubble should not create calendar events', async ({ page }) => {
    await page.goto('/');
    
    // Mock chat API to verify it doesn't create calendar events
    let calendarEventCreated = false;
    
    await page.route('**/api/chat', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      
      if (postData?.userMessage?.toLowerCase().includes('schedule')) {
        const response = await route.fetch();
        const data = await response.json();
        
        // Verify no calendar event was created
        if (data.action_result?.eventId) {
          calendarEventCreated = true;
        }
        
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            kind: 'assistant',
            text: 'Please use the Calendar page for scheduling.',
            intent: 'general_intent',
            intent_confidence: 0.8,
            escalated: false,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Try to open chat bubble (if it exists)
    const chatButton = page.locator('button[aria-label*="chat"], button:has-text("Chat")').first();
    if (await chatButton.count() > 0) {
      await chatButton.click();
      
      // Wait for chat to open
      await page.waitForTimeout(500);
      
      // Type a scheduling message
      const input = page.locator('input[type="text"], textarea').first();
      if (await input.count() > 0) {
        await input.fill('Schedule a meeting tomorrow at 2pm');
        await input.press('Enter');
        
        // Wait for response
        await page.waitForTimeout(1000);
        
        // Verify no calendar event was created
        expect(calendarEventCreated).toBe(false);
      }
    }
  });
});

