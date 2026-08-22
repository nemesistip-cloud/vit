import { test, expect } from '@playwright/test';

test('Matches page renders its real tabs, summary count, and search', async ({ page }) => {
  await page.goto('/matches');

  // Accept the gambling notice if it appears.
  const acceptButton = page.getByText('I Understand & Accept');
  if (await acceptButton.isVisible().catch(() => false)) {
    await acceptButton.click();
  }

  await expect(page.getByRole('heading', { name: /Matches & Predictions/i })).toBeVisible();

  await expect(page.getByRole('tab', { name: /Upcoming/i })).toBeVisible();
  await expect(page.getByRole('tab', { name: /Live/i })).toBeVisible();
  await expect(page.getByRole('tab', { name: /Recent/i })).toBeVisible();
  await expect(page.getByRole('tab', { name: /^All$/i })).toBeVisible();

  await expect(page.getByText(/\d+ match(?:es)?|No matches/i)).toBeVisible();

  const searchInput = page.getByPlaceholder(/Search teams or leagues/i);
  await expect(searchInput).toBeVisible();

  await page.screenshot({ path: 'matches-tabs.png' });
});
