import { test, expect } from '@playwright/test';

test('verify assistant page UI', async ({ page }) => {
  await page.goto('http://localhost:5173/assistant');
  // Wait for the card to be visible
  await expect(page.locator('.rounded-2xl.border-border\\/50')).toBeVisible();
  await page.screenshot({ path: 'assistant_ui.png' });
});

test('verify dashboard page UI', async ({ page }) => {
  await page.goto('http://localhost:5173/dashboard');
  await page.screenshot({ path: 'dashboard_ui.png' });
});

test('verify offerwall page UI', async ({ page }) => {
  await page.goto('http://localhost:5173/offerwall');
  await page.screenshot({ path: 'offerwall_ui.png' });
});
