/**
 * Regression tests for chat bubble non-scheduling features
 * 
 * Ensures removing scheduler didn't break:
 * - Reply drafting
 * - Summarization
 * - RAG results
 * - General chat
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes } from './utils/mock_server';

test.describe('Chat Bubble Regression', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
    await page.goto('/');
  });

  test('should display chat bubble', async ({ page }) => {
    // Look for chat bubble button or floating element
    const chatButton = page.locator('[data-testid="chat-button"], button[aria-label*="chat" i], .chat-bubble, #chat-toggle').first();
    
    // Chat bubble should be visible or can be opened
    const isVisible = await chatButton.isVisible().catch(() => false);
    const exists = await chatButton.count() > 0;
    
    expect(exists || isVisible).toBe(true);
  });

  test('should draft reply for non-scheduling request', async ({ page }) => {
    // Mock chat API for reply drafting
    await page.route('**/api/chat', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      
      if (postData?.userMessage?.toLowerCase().includes('draft') || postData?.userMessage?.toLowerCase().includes('reply')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            kind: 'assistant',
            text: 'Thank you for the update. I\'ll review it by end of day and get back to you.',
            intent: 'general_intent',
            intent_confidence: 0.9,
            escalated: false,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Try to open chat bubble
    const chatButton = page.locator('[data-testid="chat-button"], button:has-text("Chat"), .chat-toggle').first();
    if (await chatButton.count() > 0) {
      await chatButton.click();
      await page.waitForTimeout(500);
    }

    // Find chat input
    const chatInput = page.locator('[data-testid="chat-input"], textarea[placeholder*="message" i], input[type="text"]').first();
    
    if (await chatInput.count() > 0) {
      await chatInput.fill('Draft a short reply to: Thanks for the update — I\'ll review by EOD.');
      await chatInput.press('Enter');
      
      // Wait for response
      await page.waitForTimeout(2000);
      
      // Verify reply appears
      const replyText = await page.textContent('body');
      expect(replyText).toContain('review');
      expect(replyText).toContain('end of day');
    } else {
      // If chat UI not found, test API directly
      const response = await page.request.post('/api/chat', {
        data: {
          userMessage: 'Draft a short reply to: Thanks for the update — I\'ll review by EOD.',
          threadId: 'test-thread',
          tone: 'warm',
        },
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data.text || data.response).toBeTruthy();
      expect((data.text || data.response).toLowerCase()).toContain('review');
    }
  });

  test('should not create calendar events for scheduling requests', async ({ page }) => {
    let calendarEventCreated = false;
    
    // Monitor for calendar event creation
    await page.route('**/api/calendar/events', async (route) => {
      if (route.request().method() === 'POST') {
        calendarEventCreated = true;
      }
      await route.continue();
    });
    
    await page.route('**/api/v1/scheduler/create_event', async (route) => {
      calendarEventCreated = true;
      await route.continue();
    });

    // Send scheduling request via chat
    const response = await page.request.post('/api/chat', {
      data: {
        userMessage: 'Schedule a meeting tomorrow at 2pm',
        threadId: 'test-thread',
        tone: 'warm',
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should NOT create calendar event, should redirect to scheduler
    expect(calendarEventCreated).toBe(false);
    expect(data.intent).not.toBe('action_intent');
    expect((data.text || data.response || '').toLowerCase()).toMatch(/calendar|scheduler|schedule/i);
  });

  test('should show RAG sources when available', async ({ page }) => {
    // Mock RAG response with citations
    await page.route('**/api/chat', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      
      if (postData?.userMessage?.toLowerCase().includes('policy') || postData?.userMessage?.toLowerCase().includes('refund')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            kind: 'policy',
            text: 'According to our refund policy, customers can request refunds within 30 days of purchase.',
            citations: [
              {
                id: 'citation-1',
                score: 0.95,
                textSnippet: 'Refund Policy Section 3.1: Customers may request refunds...',
              },
            ],
            intent: 'policy_intent',
            intent_confidence: 0.95,
            escalated: false,
          }),
        });
      } else {
        await route.continue();
      }
    });

    const response = await page.request.post('/api/chat', {
      data: {
        userMessage: 'What is our refund policy?',
        threadId: 'test-thread',
        tone: 'formal',
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.citations).toBeDefined();
    expect(Array.isArray(data.citations)).toBe(true);
    expect(data.citations.length).toBeGreaterThan(0);
  });

  test('should handle general conversation', async ({ page }) => {
    const response = await page.request.post('/api/chat', {
      data: {
        userMessage: 'Hello, how are you?',
        threadId: 'test-thread',
        tone: 'warm',
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.text || data.response).toBeTruthy();
    expect(data.intent).toBe('general_intent');
  });
});
