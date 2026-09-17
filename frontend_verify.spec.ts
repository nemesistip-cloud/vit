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

test('authenticated shell exposes product layers and mobile More navigation', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'ui-shell-smoke-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'operator', role: 'admin' }));
  });

  await page.goto('/workspace');
  const sidebar = page.getByRole('complementary');
  await expect(sidebar.getByText('Explore', { exact: true })).toBeVisible();
  await expect(sidebar.getByText('Workspace', { exact: true })).toBeVisible();
  await expect(sidebar.getByText('Ecosystem', { exact: true })).toBeVisible();
  await expect(sidebar.getByText('Admin Control', { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('button', { name: 'Open more navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Open more navigation' }).click();
  const moreMenu = page.locator('div.absolute.bottom-full');
  await expect(moreMenu.getByRole('link', { name: 'Explorer', exact: true })).toBeVisible();
  await expect(moreMenu.getByRole('link', { name: 'Governance', exact: true })).toBeVisible();

  await page.screenshot({ path: 'authenticated-shell-mobile.png' });
});
