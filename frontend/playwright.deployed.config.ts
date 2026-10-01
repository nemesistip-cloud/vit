import { defineConfig } from '@playwright/test'

const baseURL = process.env.VIT_DEPLOYED_BASE_URL?.replace(/\/+$/, '')

if (!baseURL) {
  throw new Error('Set VIT_DEPLOYED_BASE_URL to the deployed VIT Network base URL')
}

export default defineConfig({
  testDir: '.',
  testMatch: /deployed_smoke\.spec\.ts$/,
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  reporter: [['list']],
  retries: 0,
  workers: 1,
  use: {
    baseURL,
    headless: true,
    trace: 'off',
    viewport: { width: 1440, height: 1200 },
  },
})