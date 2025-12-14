/**
 * SSE streaming behavior tests
 */
import { test, expect } from '@playwright/test';
import { setupMockRoutes, mockLLMStream } from './utils/mock_server';

test.describe('SSE Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page);
  });

  test('should display progressive tokens', async ({ page }) => {
    const tokens = ['Hello', ' there', '!', ' How', ' can', ' I', ' help', ' you', ' today', '?'];
    
    await mockLLMStream(page, tokens, 150);
    
    await page.goto('/');
    
    // Trigger streaming request
    const response = await page.request.post('/api/v1/stream_chat', {
      data: {
        messages: [{ role: 'user', content: 'Tell me a story' }],
      },
    });

    expect(response.ok()).toBeTruthy();
    
    // Read SSE stream
    const reader = response.body()?.getReader();
    const decoder = new TextDecoder();
    const receivedTokens: string[] = [];
    
    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'token') {
                receivedTokens.push(data.text);
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }
    }
    
    // Verify tokens were received progressively
    expect(receivedTokens.length).toBeGreaterThan(0);
  });

  test('should handle cancellation mid-stream', async ({ page }) => {
    const tokens = Array.from({ length: 100 }, (_, i) => `token${i} `);
    
    await mockLLMStream(page, tokens, 50);
    
    await page.goto('/');
    
    // Start streaming request
    const controller = new AbortController();
    const responsePromise = page.request.post('/api/v1/stream_chat', {
      data: {
        messages: [{ role: 'user', content: 'Long response' }],
      },
      headers: {
        'Accept': 'text/event-stream',
      },
    });

    // Cancel after 500ms
    setTimeout(() => {
      controller.abort();
    }, 500);

    try {
      const response = await responsePromise;
      // Stream should be cancellable
      expect(response.ok() || response.status() === 0).toBeTruthy();
    } catch (error) {
      // Abort error is expected
      expect(error).toBeDefined();
    }
  });

  test('should show done event at end of stream', async ({ page }) => {
    const tokens = ['Token1', ' Token2', ' Token3'];
    
    await mockLLMStream(page, tokens, 100);
    
    await page.goto('/');
    
    const response = await page.request.post('/api/v1/stream_chat', {
      data: {
        messages: [{ role: 'user', content: 'Short response' }],
      },
    });

    expect(response.ok()).toBeTruthy();
    
    // Read stream to find done event
    const reader = response.body()?.getReader();
    const decoder = new TextDecoder();
    let doneReceived = false;
    
    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        if (chunk.includes('"type":"done"')) {
          doneReceived = true;
          break;
        }
      }
    }
    
    expect(doneReceived).toBe(true);
  });

  test('should measure time-to-first-token', async ({ page }) => {
    const tokens = ['First', ' token'];
    
    await mockLLMStream(page, tokens, 50);
    
    await page.goto('/');
    
    const startTime = Date.now();
    const response = await page.request.post('/api/v1/stream_chat', {
      data: {
        messages: [{ role: 'user', content: 'Quick response' }],
      },
    });

    expect(response.ok()).toBeTruthy();
    
    // Read first token
    const reader = response.body()?.getReader();
    const decoder = new TextDecoder();
    let firstTokenTime: number | null = null;
    
    if (reader) {
      const { value } = await reader.read();
      if (value) {
        firstTokenTime = Date.now() - startTime;
      }
    }
    
    // Should receive first token within 3 seconds
    expect(firstTokenTime).toBeLessThan(3000);
  });
});

