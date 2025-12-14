# UI Test Suite Checklist

## Installation Status

- [ ] `npm install` completed in `frontend/`
- [ ] `npx playwright install --with-deps` completed
- [ ] Test backend dependencies installed (if using real backend)
- [ ] Test database created and migrated

## Test Execution Status

### Smoke Tests (Quick Validation)
```bash
npm run test:ui:smoke
```
- [ ] All smoke tests pass
- [ ] No critical errors

### Full Test Suite
```bash
npm run test:ui
```
- [ ] All tests pass across browsers
- [ ] Visual baselines match
- [ ] Accessibility checks pass
- [ ] No flaky tests

## Test Coverage Verification

### Chat Bubble (Non-Scheduling)
- [ ] Reply drafting works
- [ ] RAG sources appear
- [ ] General conversation works
- [ ] No calendar events created from chat

### Scheduler Flow
- [ ] NL parsing works
- [ ] Preview modal displays correctly
- [ ] Event creation succeeds
- [ ] Reminder scheduling works
- [ ] Conflict handling works
- [ ] Recurring events work

### Calendar Connect
- [ ] OAuth URL generation works
- [ ] Callback handling works
- [ ] Token expiry re-auth works

### Event Management
- [ ] Event list displays
- [ ] Reschedule works
- [ ] Cancel works
- [ ] Provider badges show

### Notifications
- [ ] In-app notifications appear
- [ ] Email notifications (mocked) work
- [ ] Slack notifications (mocked) work
- [ ] Snooze works

### SSE Streaming
- [ ] Progressive tokens appear
- [ ] Cancellation works
- [ ] Time-to-first-token < 3s

### Responsiveness
- [ ] Mobile (375x812) works
- [ ] Tablet (768x1024) works
- [ ] Desktop (1366x768) works

### Accessibility
- [ ] Home page passes axe checks
- [ ] Calendar page passes axe checks
- [ ] Connect page passes axe checks
- [ ] Scheduler modal passes axe checks

### Visual Regression
- [ ] Home page baseline matches
- [ ] Calendar page baseline matches
- [ ] Connect page baseline matches
- [ ] Scheduler modal baseline matches

## Artifacts Review

- [ ] Screenshots saved on failures
- [ ] Traces generated for failures
- [ ] Accessibility reports generated
- [ ] Visual diffs saved
- [ ] HTML report generated

## Known Issues

List any known issues or flaky tests:

1. 
2. 
3. 

## Recommendations

### Selector Stability
- [ ] Add `data-testid` to chat bubble elements
- [ ] Add `data-testid` to scheduler modal elements
- [ ] Add `data-testid` to calendar event elements

### Performance
- [ ] Time-to-first-token < 3s
- [ ] Page load < 2s
- [ ] API response times acceptable

### Accessibility
- [ ] All critical violations fixed
- [ ] Keyboard navigation works
- [ ] Screen reader compatible

## Next Actions

- [ ] Review test failures (if any)
- [ ] Update baselines if UI changed intentionally
- [ ] Add tests for new features
- [ ] Update mock server for API changes
- [ ] Document any test-specific setup requirements

