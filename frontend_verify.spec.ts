import { test, expect } from '@playwright/test';

test('Match detail page renders the actual fixture heading and title', async ({ page }) => {
  const match = {
    id: 360,
    home_team: 'Arsenal',
    away_team: 'Liverpool',
    league: 'Premier League',
    sport: 'football',
    kickoff_time: '2026-09-18T19:45:00Z',
    status: 'scheduled',
    data_status: 'CACHED',
    home_prob: 0.46,
    draw_prob: 0.28,
    away_prob: 0.26,
    odds: { home: 2.3, draw: 3.4, away: 3.1 },
    intelligence: {
      consensus: { home_prob: 0.46, draw_prob: 0.28, away_prob: 0.26, confidence: 0.62, risk_score: 0.18, model_agreement: 0.73, models_active: 7 },
      attribution: [{ model_name: 'xgboost', bet_side: 'home', confidence: 0.62, final_ev: 0.12, entry_odds: 2.3, reasoning: 'Strong form and set-piece edge' }],
    },
  };

  await page.route('**/api/matches/360', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(match) });
  });

  await page.goto('/matches/360');

  await expect(page.getByRole('heading', { name: /Arsenal vs Liverpool/i })).toBeVisible();
  await expect(page).toHaveTitle(/Arsenal vs Liverpool/i);
  await expect(page.getByText('Premier League')).toBeVisible();
});

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
