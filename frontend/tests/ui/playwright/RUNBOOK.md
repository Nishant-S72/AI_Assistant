# UI Test Runbook

## Quick Reference

### Run Full Suite
```bash
cd frontend && npm run test:ui
```

### Run Smoke Tests
```bash
cd frontend && npm run test:ui:smoke
```

### Update Baselines
```bash
cd frontend && npm run test:ui:update
```

## Interpreting Test Failures

### 1. Selector Not Found

**Symptom**: `Error: locator.click: Target closed`

**Cause**: UI element not found or changed selector

**Fix**:
1. Check if element exists in DOM: `await page.locator('selector').count()`
2. Add `data-testid` attribute to element
3. Use more stable selector (role, aria-label)
4. Increase wait timeout

**Example**:
```typescript
// Bad
await page.locator('.chat-button').click();

// Good
await page.locator('[data-testid="chat-button"]').click();
```

### 2. Mock Server Mismatch

**Symptom**: `404 Not Found` or unexpected API response

**Cause**: Route handler not matching or missing

**Fix**:
1. Check `utils/mock_server.ts` for route handler
2. Verify route pattern matches actual API endpoint
3. Check request method (GET vs POST)
4. Add console.log to see actual request URL

**Example**:
```typescript
// Add logging
await page.route('**/api/v1/scheduler/events**', async (route) => {
  console.log('Mocking:', route.request().url());
  await route.fulfill({ ... });
});
```

### 3. OAuth Popup Issues

**Symptom**: Test hangs waiting for OAuth popup

**Cause**: Real OAuth popup opened instead of mock

**Fix**:
1. Verify mock route is set up before navigation
2. Check that OAuth URL is mocked, not real
3. Use `page.waitForEvent('popup')` if real popup needed

**Example**:
```typescript
// Mock OAuth before clicking
await page.route('**/api/v1/scheduler/connect/google**', async (route) => {
  await route.fulfill({
    body: JSON.stringify({ oauth_url: 'http://localhost/mock-oauth' })
  });
});
```

### 4. Visual Regression False Positives

**Symptom**: Screenshot diff for unchanged UI

**Cause**: Dynamic content (timestamps, random IDs, animations)

**Fix**:
1. Mask dynamic elements: `await expect(page).toHaveScreenshot({ mask: ['.timestamp'] })`
2. Wait for animations: `await page.waitForLoadState('networkidle')`
3. Increase threshold: `maxDiffPixels: 500`
4. Update baseline if intentional change

**Example**:
```typescript
await expect(page).toHaveScreenshot('page.png', {
  mask: [page.locator('.timestamp'), page.locator('[data-random-id]')],
  maxDiffPixels: 100,
});
```

### 5. Timeout Errors

**Symptom**: `Timeout 30000ms exceeded`

**Cause**: Slow network, heavy computation, or element not appearing

**Fix**:
1. Increase timeout: `await page.waitForSelector('...', { timeout: 60000 })`
2. Check network tab for slow requests
3. Verify element actually appears (manual test)
4. Add explicit wait: `await page.waitForLoadState('networkidle')`

### 6. Accessibility Violations

**Symptom**: Axe reports critical violations

**Cause**: Missing ARIA labels, color contrast, keyboard navigation

**Fix**:
1. Review accessibility report: `artifacts/accessibility/*.json`
2. Fix violations in source code
3. Add exceptions with justification if needed

**Example**:
```typescript
await checkA11y(page, {
  rules: {
    'color-contrast': { enabled: false }, // Temporary exception
  },
});
```

### 7. SSE Streaming Issues

**Symptom**: Tokens not appearing or stream hangs

**Cause**: Mock stream not properly formatted or cancelled

**Fix**:
1. Verify SSE format: `data: {...}\n\n`
2. Check stream is properly closed
3. Test cancellation with AbortController

**Example**:
```typescript
// Proper SSE format
controller.enqueue(new TextEncoder().encode(
  `data: ${JSON.stringify({ type: 'token', text: 'Hello' })}\n\n`
));
```

### 8. Concurrent Test Failures

**Symptom**: Race conditions, flaky tests

**Cause**: Shared state, timing issues

**Fix**:
1. Use `test.describe.serial()` for dependent tests
2. Reset state between tests
3. Use `page.waitForFunction()` for async conditions
4. Add retries: `test.retries(2)`

## Debugging Workflow

### Step 1: View Trace
```bash
npx playwright show-trace artifacts/trace.zip
```

### Step 2: Check Screenshots
```bash
open artifacts/screenshots/
```

### Step 3: Review Network Logs
Check `artifacts/logs.json` for API calls

### Step 4: Run in UI Mode
```bash
npx playwright test --ui
```

### Step 5: Add Debug Logging
```typescript
await page.route('**/api/**', async (route) => {
  console.log('API Call:', route.request().url());
  await route.continue();
});
```

## Common Selector Patterns

### Stable Selectors (Preferred)
```typescript
// data-testid (best)
page.locator('[data-testid="chat-button"]')

// role + name
page.locator('button[name="Submit"]')

// aria-label
page.locator('[aria-label="Close modal"]')
```

### Fallback Selectors
```typescript
// Text content (fragile)
page.locator('text=Submit')

// CSS class (avoid if possible)
page.locator('.submit-button')
```

## Test Data Management

### Seeding Test Data
```typescript
// In setup.ts or test file
await page.request.post('/api/test/seed', {
  data: {
    user: { email: 'test@example.com' },
    events: [...],
  },
});
```

### Cleaning Up
```typescript
test.afterEach(async ({ page }) => {
  await page.request.post('/api/test/cleanup');
});
```

## Performance Testing

### Measure Load Time
```typescript
const startTime = Date.now();
await page.goto('/');
await page.waitForLoadState('networkidle');
const loadTime = Date.now() - startTime;
expect(loadTime).toBeLessThan(3000);
```

### Network Throttling
```typescript
test.use({
  contextOptions: {
    ...devices['Desktop Chrome'],
    // Slow 3G
    connection: { download: 400, upload: 400, latency: 400 },
  },
});
```

## CI/CD Debugging

### Local Reproduction
```bash
# Match CI environment
export CI=true
export SKIP_BACKEND=false
npx playwright test
```

### Check CI Artifacts
1. Download `playwright-report` artifact
2. Open `index.html` in browser
3. Review failed test traces

## Maintenance Checklist

- [ ] Update baselines when UI changes
- [ ] Review accessibility reports monthly
- [ ] Update mock server when APIs change
- [ ] Add tests for new features
- [ ] Remove obsolete tests
- [ ] Keep selectors stable (use data-testid)

## Getting Help

1. Check test artifacts first
2. Review Playwright documentation
3. Check mock server implementation
4. Open issue with:
   - Test output
   - Screenshots
   - Trace file
   - Reproduction steps

