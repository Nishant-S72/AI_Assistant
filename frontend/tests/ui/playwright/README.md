# Playwright UI Test Suite

Complete end-to-end test suite for the AI Assistant application, covering chat bubble, scheduler, calendar integration, and responsive behavior.

## Prerequisites

- Node.js 18+
- Python 3.11+ (for test backend)
- PostgreSQL (for test database)
- Playwright browsers installed

## Installation

```bash
# Install frontend dependencies
cd frontend
npm ci

# Install Playwright browsers
npx playwright install --with-deps

# Install backend test dependencies (if running test backend)
cd ../backend_python
pip install -r requirements.txt
```

## Running Tests

### Full Test Suite

Run all tests across all browsers and viewports:

```bash
npx playwright test --project=all --reporter=list --output=tests/ui/playwright/artifacts
```

### Smoke Tests (Quick)

Run critical path tests only:

```bash
npx playwright test tests/ui/playwright/test_scheduler_flow.spec.ts --project=chromium --workers=1
```

### Specific Test File

```bash
npx playwright test tests/ui/playwright/test_chat_bubble_regression.spec.ts
```

### Update Visual Baselines

When UI changes intentionally, update screenshot baselines:

```bash
npx playwright test --update-snapshots
```

### Run in UI Mode (Interactive)

```bash
npx playwright test --ui
```

## Test Structure

```
tests/ui/playwright/
├── playwright.config.ts          # Playwright configuration
├── setup.ts                      # Global setup/teardown
├── test_scheduler_flow.spec.ts    # Scheduler E2E flow
├── test_chat_bubble_regression.spec.ts  # Chat bubble non-scheduling
├── test_connect_calendar.spec.ts  # Calendar OAuth connect
├── test_event_list_and_edit.spec.ts  # Event CRUD operations
├── test_notifications.spec.ts    # Notification delivery
├── test_sse_streaming.spec.ts    # SSE streaming behavior
├── test_responsiveness.spec.ts   # Mobile/tablet/desktop
├── test_accessibility.spec.ts    # Axe accessibility checks
├── test_visual_regression.spec.ts  # Visual snapshots
├── utils/
│   └── mock_server.ts            # Mock API handlers
└── artifacts/                    # Test outputs
    ├── screenshots/
    ├── traces/
    ├── accessibility/
    ├── visual-diffs/
    └── logs.json
```

## Test Backend

Tests use mocked API endpoints by default. To run against a real test backend:

1. Set up test database:
```bash
createdb aichief_test
psql aichief_test -f backend_python/db/migrations/006_create_scheduler_tables.sql
```

2. Set environment variables:
```bash
export TEST_DATABASE_URL=postgres://postgres:postgres@localhost:5432/aichief_test
export SKIP_BACKEND=false
```

3. Run tests (backend will start automatically):
```bash
npx playwright test
```

## Mock Server

All external integrations are mocked:
- LLM API calls → Mock responses
- Google/Outlook Calendar → Mock OAuth and API
- SMTP/Slack → Mock notification delivery
- SSE streaming → Mock event stream

See `utils/mock_server.ts` for implementation.

## Artifacts

Test artifacts are saved to `tests/ui/playwright/artifacts/`:

- **screenshots/**: Failure screenshots
- **traces/**: Playwright traces for debugging
- **accessibility/**: Axe accessibility reports (JSON + HTML)
- **visual-diffs/**: Visual regression diffs
- **html-report/**: HTML test report
- **results.json**: Test results in JSON format

## Debugging Failures

### View Trace

```bash
npx playwright show-trace tests/ui/playwright/artifacts/trace.zip
```

### Common Issues

1. **Selector not found**: Add `data-testid` attributes to UI elements
2. **Mock server mismatch**: Check `utils/mock_server.ts` route handlers
3. **OAuth popup**: OAuth flows are mocked, no real popup should appear
4. **Timeout**: Increase timeout in `playwright.config.ts` or test-specific timeout

### Selector Strategy

Use stable selectors:
- `data-testid` attributes (preferred)
- Semantic HTML (`role`, `aria-label`)
- Text content (as fallback)

Avoid:
- CSS class names (can change)
- XPath (fragile)
- Position-based selectors

## CI Integration

See `.github/workflows/ui-tests.yml` for GitHub Actions configuration.

Tests run on:
- Pull requests
- Main branch pushes
- Manual workflow dispatch

## Test Coverage

### ✅ Covered

- Chat bubble non-scheduling features
- Scheduler flow (parse → preview → confirm)
- Calendar OAuth connect
- Event list, edit, cancel
- Notification delivery (mocked)
- SSE streaming
- Responsive design (mobile/tablet/desktop)
- Accessibility (WCAG 2.1 AA)
- Visual regression

### 🔄 Edge Cases

- Concurrent event creation
- Malformed time strings
- DST boundary crossing
- Token expiry handling
- Stream cancellation

## Updating Tests

When adding new features:

1. Add test file: `test_<feature>.spec.ts`
2. Update mock server if needed: `utils/mock_server.ts`
3. Add visual baseline if UI changes
4. Update this README

## Troubleshooting

### Tests fail locally but pass in CI

- Check environment variables
- Verify test database state
- Clear Playwright cache: `npx playwright install --force`

### Visual regression false positives

- Update baseline: `npx playwright test --update-snapshots`
- Check for dynamic content (timestamps, random IDs)
- Use `maxDiffPixels` or `threshold` options

### Accessibility violations

- Fix violations in source code
- Or add exceptions in test with justification

## Support

For issues or questions:
1. Check test artifacts for detailed error messages
2. Review Playwright trace files
3. Check mock server logs
4. Open issue with test output and reproduction steps

