import { test, expect } from '@playwright/test';

test('Matches page has tabs and dynamic counts', async ({ page }) => {
  await page.goto('/matches');

  // Accept the gambling notice if it appears
  const acceptButton = page.getByText('I Understand & Accept');
  if (await acceptButton.isVisible()) {
    await acceptButton.click();
  }

  // Check for the "Matches" and "Teams" tabs
  await expect(page.getByRole('tab', { name: /Matches/ })).toBeVisible();
  await expect(page.getByRole('tab', { name: /Teams/ })).toBeVisible();

  // Check for the dynamic count in the summary line
  await expect(page.getByText(/Matches found:/)).toBeVisible();

  // Switch to Teams tab
  await page.getByRole('tab', { name: /Teams/ }).click();
  await expect(page.getByText(/Teams found:/)).toBeVisible();

  // Verify search input placeholder changes
  const searchInput = page.getByPlaceholder(/Search teams/);
  await expect(searchInput).toBeVisible();

  await page.screenshot({ path: 'matches-tabs.png' });
});
