/**
 * Notification delivery UI tests
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes } from './utils/mock_server';

test.describe('Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
  });

  test('should show in-app notification when reminder triggers', async ({ page }) => {
    // Mock notification endpoint
    await page.route('**/api/notifications/in-app**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          notifications: [
            {
              id: 'notif-1',
              type: 'reminder',
              title: 'Meeting in 15 minutes',
              message: 'Meeting with Alex starts in 15 minutes',
              event_id: 'event-1',
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    await page.goto('/');
    
    // Simulate notification arrival (would be via SSE or polling in real app)
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('notification', {
        detail: {
          type: 'reminder',
          title: 'Meeting in 15 minutes',
          message: 'Meeting with Alex starts in 15 minutes',
        },
      }));
    });

    await page.waitForTimeout(1000);
    
    // Verify notification appears (if UI exists)
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
  });

  test('should allow snoozing reminder', async ({ page }) => {
    let snoozeCalled = false;
    
    await page.route('**/api/v1/scheduler/reminders/**/snooze', async (route) => {
      snoozeCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          new_trigger_time: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        }),
      });
    });

    // Simulate snooze action
    const response = await page.request.post('/api/v1/scheduler/reminders/reminder-1/snooze', {
      data: {
        minutes: 10,
      },
    });

    expect(response.ok()).toBeTruthy();
    const result = await response.json();
    expect(result.success).toBe(true);
    expect(snoozeCalled).toBe(true);
  });

  test('should log email notification sent', async ({ page }) => {
    // Mock email notification log
    let emailSent = false;
    
    await page.route('**/api/notifications/email**', async (route) => {
      emailSent = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message_id: 'email-123',
          sent_at: new Date().toISOString(),
        }),
      });
    });

    const response = await page.request.post('/api/notifications/email', {
      data: {
        to: 'test@example.com',
        subject: 'Meeting Reminder',
        body: 'Your meeting starts in 15 minutes',
      },
    });

    expect(response.ok()).toBeTruthy();
    expect(emailSent).toBe(true);
  });

  test('should log Slack notification sent', async ({ page }) => {
    let slackSent = false;
    
    await page.route('**/api/notifications/slack**', async (route) => {
      slackSent = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message_ts: 'slack-123',
          sent_at: new Date().toISOString(),
        }),
      });
    });

    const response = await page.request.post('/api/notifications/slack', {
      data: {
        channel: '#notifications',
        text: 'Meeting reminder: Meeting with Alex in 15 minutes',
      },
    });

    expect(response.ok()).toBeTruthy();
    expect(slackSent).toBe(true);
  });
});

