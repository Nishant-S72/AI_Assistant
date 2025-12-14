import { defineConfig, devices } from '@playwright/test';
import path from 'path';

/**
 * Playwright configuration for UI test suite
 * 
 * Runs tests across Chromium, Firefox, and WebKit
 * Captures traces, screenshots, and accessibility reports on failure
 */
export default defineConfig({
  testDir: './',
  
  // Maximum time one test can run
  timeout: 60 * 1000,
  
  // Test execution
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 4,
  
  // Reporter configuration
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/ui/playwright/artifacts/html-report' }],
    ['json', { outputFile: 'tests/ui/playwright/artifacts/results.json' }],
    ['junit', { outputFile: 'tests/ui/playwright/artifacts/junit.xml' }],
  ],
  
  // Shared settings for all projects
  use: {
    // Base URL for tests
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
    
    // Action timeout
    actionTimeout: 15 * 1000,
    
    // Navigation timeout
    navigationTimeout: 30 * 1000,
  },
  
  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile viewports
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
    // Tablet
    {
      name: 'tablet',
      use: { ...devices['iPad Pro'] },
    },
  ],
  
  // Run local dev server before tests (disabled by default, use mocks)
  // webServer: process.env.SKIP_BACKEND ? undefined : {
  //   command: 'cd ../../backend_python && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001',
  //   url: 'http://localhost:8001/api/health',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  //   env: {
  //     DATABASE_URL: process.env.TEST_DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/aichief_test',
  //     USE_OLLAMA: 'false',
  //     OPENAI_API_KEY: 'test-key',
  //     NEW_SCHEDULER_ENABLED: 'true',
  //     GOOGLE_CLIENT_ID: 'test-google-client-id',
  //     GOOGLE_CLIENT_SECRET: 'test-google-secret',
  //     OUTLOOK_CLIENT_ID: 'test-outlook-client-id',
  //     OUTLOOK_CLIENT_SECRET: 'test-outlook-secret',
  //   },
  // },
  
  // Output directory for artifacts
  outputDir: 'tests/ui/playwright/artifacts/test-results',
  
  // Global setup/teardown
  globalSetup: require.resolve('./setup.ts'),
});
