import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: /frontend_verify\.spec\.ts$/,
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5000',
    headless: true,
    trace: 'on-first-retry',
    viewport: { width: 1440, height: 1200 },
  },
  webServer: {
    command: 'npm run dev --prefix frontend',
    url: 'http://127.0.0.1:5000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
