/**
 * Mock server utilities for Playwright tests
 * 
 * Provides route handlers to mock:
 * - LLM API calls
 * - Google/Outlook Calendar APIs
 * - OAuth flows
 * - SMTP/Slack notifications
 * - SSE streaming
 */

import { Page, Route } from '@playwright/test';

export interface MockLLMResponse {
  content: string;
  function_call?: {
    name: string;
    arguments: string | Record<string, any>;
  };
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface MockCalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  attendees?: string[];
  location?: string;
  description?: string;
}

/**
 * Setup mock routes for a page
 */
export async function setupMockRoutes(page: Page) {
  // Mock LLM API calls
  await page.route('**/api/chat', async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();
    
    if (postData?.userMessage?.toLowerCase().includes('schedule')) {
      // Scheduling request - return redirect message
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kind: 'assistant',
          text: 'I can help you schedule meetings! Please use the Calendar page or the dedicated scheduler interface.',
          intent: 'general_intent',
          intent_confidence: 0.8,
          escalated: false,
        }),
      });
    } else {
      // General chat - return mock response
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kind: 'assistant',
          text: 'This is a mock response for: ' + postData?.userMessage,
          intent: 'general_intent',
          intent_confidence: 0.9,
          escalated: false,
        }),
      });
    }
  });
  
  // Mock scheduler chat endpoint
  await page.route('**/api/v1/scheduler/chat', async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();
    const messages = postData?.messages || [];
    const lastMessage = messages[messages.length - 1]?.content || '';
    
    // Mock LLM function calling response
    if (lastMessage.toLowerCase().includes('schedule') || lastMessage.toLowerCase().includes('meeting')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'I\'ll help you schedule that meeting.',
          function_call: {
            name: 'parse_schedule',
            result: {
              title: 'Meeting with Alex',
              start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
              end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
              attendees: ['alex@example.com'],
              timezone: 'Asia/Kolkata',
              description: '30 min call',
            },
          },
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'How can I help you with scheduling?',
        }),
      });
    }
  });
  
  // Mock parse schedule endpoint
  await page.route('**/api/v1/scheduler/parse', async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();
    const text = postData?.natural_language || '';
    
    // Extract time from text
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(15, 0, 0, 0);
    
    // Extract attendees from text
    const attendees: string[] = [];
    if (text.toLowerCase().includes('alex')) {
      attendees.push('alex@example.com');
    }
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        title: text.includes('Alex') ? 'Meeting with Alex' : 'Meeting',
        start_time: tomorrow.toISOString(),
        end_time: new Date(tomorrow.getTime() + 30 * 60 * 1000).toISOString(),
        attendees: attendees,
        timezone: 'Asia/Kolkata',
        description: text,
      }),
    });
  });
  
  // Mock create event endpoint (can be overridden in tests)
  await page.route('**/api/v1/scheduler/create_event', async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        event_id: 'mock-event-' + Date.now(),
        external_event_id: 'google-event-123',
        title: postData?.title || 'Meeting',
        start_time: postData?.start_time || new Date().toISOString(),
        end_time: postData?.end_time || new Date(Date.now() + 3600000).toISOString(),
      }),
    });
  });
  
  // Mock list events endpoint
  await page.route('**/api/v1/scheduler/events**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [
          {
            id: 'event-1',
            title: 'Test Meeting',
            start_time: new Date().toISOString(),
            end_time: new Date(Date.now() + 3600000).toISOString(),
            description: 'Test event',
            calendar_provider: 'google',
            status: 'confirmed',
          },
        ],
      }),
    });
  });
  
  // Mock Google OAuth connect
  await page.route('**/api/v1/scheduler/connect/google**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        oauth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=http://localhost:3000/callback&state=mock-state',
        state: 'mock-state',
      }),
    });
  });
  
  // Mock Outlook OAuth connect
  await page.route('**/api/v1/scheduler/connect/outlook**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        oauth_url: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=test&redirect_uri=http://localhost:3000/callback&state=mock-state',
        state: 'mock-state',
      }),
    });
  });
  
  // Mock OAuth callback
  await page.route('**/api/v1/scheduler/oauth2callback/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        provider: route.request().url().includes('google') ? 'google' : 'outlook',
      }),
    });
  });
  
  // Mock find availability
  await page.route('**/api/v1/scheduler/find_availability', async (route) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(14, 0, 0, 0);
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        available_slots: [
          {
            start: tomorrow.toISOString(),
            end: new Date(tomorrow.getTime() + 60 * 60 * 1000).toISOString(),
          },
        ],
        duration_minutes: 60,
      }),
    });
  });
  
  // Mock SSE streaming endpoint
  await page.route('**/api/v1/stream_chat', async (route) => {
    const request = route.request();
    
    // Simulate SSE stream
    const stream = new ReadableStream({
      async start(controller) {
        const tokens = ['Hello', ' there', '!', ' How', ' can', ' I', ' help', '?'];
        for (const token of tokens) {
          controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: 'token', text: token })}\n\n`));
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`));
        controller.close();
      },
    });
    
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: stream,
    });
  });
}

/**
 * Mock LLM streaming response
 */
export async function mockLLMStream(page: Page, tokens: string[], delay: number = 100) {
  let tokenIndex = 0;
  
  await page.route('**/api/v1/stream_chat', async (route) => {
    const stream = new ReadableStream({
      async start(controller) {
        for (const token of tokens) {
          controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: 'token', text: token })}\n\n`));
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`));
        controller.close();
      },
    });
    
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: stream,
    });
  });
}

/**
 * Wait for mock event to be created in backend (for verification)
 */
export async function waitForEventCreated(page: Page, eventId: string, timeout: number = 5000): Promise<boolean> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await page.request.get(`/api/v1/scheduler/events`);
      const data = await response.json();
      const events = data.events || [];
      
      if (events.some((e: any) => e.id === eventId)) {
        return true;
      }
    } catch (error) {
      // Ignore errors, retry
    }
    
    await page.waitForTimeout(500);
  }
  
  return false;
}
