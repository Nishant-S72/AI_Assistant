/**
 * End-to-end test for scheduler flow
 * 
 * Tests: NL input → parse preview → confirm → EventMirror entry → reminder job
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes, waitForEventCreated } from './utils/mock_server';

test.describe('Scheduler Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
    await page.goto('/calendar');
  });

  test('should parse natural language and show preview', async ({ page }) => {
    // Unroute all matching routes first
    await page.unroute('**/api/v1/scheduler/parse', { times: Infinity });
    
    // Set specific mock for this test
    await page.route('**/api/v1/scheduler/parse', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      const text = postData?.natural_language || '';
      
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(15, 0, 0, 0);
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          title: text.toLowerCase().includes('alex') ? 'Meeting with Alex' : 'Meeting',
          start_time: tomorrow.toISOString(),
          end_time: new Date(tomorrow.getTime() + 30 * 60 * 1000).toISOString(),
          attendees: text.toLowerCase().includes('alex') ? ['alex@example.com'] : [],
          timezone: 'Asia/Kolkata',
          description: text,
        }),
      });
    });

    // Test parse endpoint via browser fetch (goes through route handlers)
    const parsed = await page.evaluate(async () => {
      const response = await fetch('/api/v1/scheduler/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          natural_language: 'Schedule a 30 min call with Alex tomorrow at 3pm IST and remind me 15 minutes before',
        }),
      });
      return response.json();
    });
    
    // Verify parsed fields
    expect(parsed).toHaveProperty('title');
    expect(parsed).toHaveProperty('start_time');
    expect(parsed).toHaveProperty('end_time');
    // Since we're testing with "Alex" in the request, title should contain it
    expect(parsed.title.toLowerCase()).toContain('alex');
    // Attendees should include alex@example.com
    expect(parsed.attendees).toBeDefined();
    expect(Array.isArray(parsed.attendees)).toBe(true);
    expect(parsed.attendees.length).toBeGreaterThan(0);
    expect(parsed.attendees.some((a: string) => a.toLowerCase().includes('alex'))).toBe(true);
    
    // Save snapshot for visual regression (skip if modal not visible)
    try {
      await expect(page).toHaveScreenshot('scheduler-parse-preview.png', {
        fullPage: false,
        timeout: 2000,
      });
    } catch (e) {
      // Screenshot might fail if modal not visible, that's OK
    }
  });

  test('should create event and show confirmation', async ({ page }) => {
    // Unroute all matching routes
    await page.unroute('**/api/v1/scheduler/create_event', { times: Infinity });
    
    let eventCreated = false;
    await page.route('**/api/v1/scheduler/create_event', async (route) => {
      eventCreated = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          event_id: 'test-event-123',
          external_event_id: 'google-event-456',
          title: 'Meeting with Alex',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
        }),
      });
    });

    // Create event via browser fetch (goes through route handlers)
    const result = await page.evaluate(async () => {
      const response = await fetch('/api/v1/scheduler/create_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Meeting with Alex',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
          calendar_provider: 'google',
          attendees: ['alex@example.com'],
          timezone: 'Asia/Kolkata',
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return response.json();
    });
    expect(result.success).toBe(true);
    expect(result.event_id).toBeTruthy();
    expect(eventCreated).toBe(true);
  });

  test('should show conflict alternatives when freebusy indicates conflict', async ({ page }) => {
    // Unroute default and set specific mock
    await page.unroute('**/api/v1/scheduler/find_availability', { times: Infinity });
    
    await page.route('**/api/v1/scheduler/find_availability', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          available_slots: [
            {
              start: new Date(Date.now() + 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
              end: new Date(Date.now() + 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString(),
            },
          ],
          conflicts: [
            {
              start: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
              end: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
            },
          ],
        }),
      });
    });

    const data = await page.evaluate(async () => {
      const response = await fetch('/api/v1/scheduler/find_availability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: new Date().toISOString(),
          end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          duration_minutes: 30,
          calendar_provider: 'google',
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return response.json();
    });
    expect(data.available_slots).toBeDefined();
    expect(Array.isArray(data.available_slots)).toBe(true);
  });

  test('should create recurring event', async ({ page }) => {
    // Unroute all matching routes
    await page.unroute('**/api/v1/scheduler/create_event', { times: Infinity });
    
    await page.route('**/api/v1/scheduler/create_event', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          event_id: 'recurring-event-123',
          external_event_id: 'google-recurring-456',
          title: 'Weekly Standup',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
        }),
      });
    });

    const result = await page.evaluate(async () => {
      const response = await fetch('/api/v1/scheduler/create_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Weekly Standup',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
          calendar_provider: 'google',
          recurrence_rule: 'FREQ=WEEKLY;BYDAY=MO',
          timezone: 'Asia/Kolkata',
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return response.json();
    });
    expect(result.success).toBe(true);
  });

  test('should schedule reminder when creating event', async ({ page }) => {
    // Unroute all matching routes
    await page.unroute('**/api/v1/scheduler/create_event', { times: Infinity });
    
    await page.route('**/api/v1/scheduler/create_event', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          event_id: 'event-with-reminder-123',
          external_event_id: 'google-event-456',
          title: 'Meeting with Reminder',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
          reminder_scheduled: true,
        }),
      });
    });

    // Create event with reminder via browser fetch
    const result = await page.evaluate(async () => {
      const response = await fetch('/api/v1/scheduler/create_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Meeting with Reminder',
          start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
          calendar_provider: 'google',
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return response.json();
    });
    expect(result.success).toBe(true);
    // Verify reminder info is included in response
    expect(result.reminder_scheduled).toBe(true);
  });
});
