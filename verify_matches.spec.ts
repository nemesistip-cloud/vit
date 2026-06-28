import { test, expect } from '@playwright/test';

test('verify match detail page robustness', async ({ page }) => {
  // Setup: bypass onboarding and disclaimers
  await page.addInitScript(() => {
    window.localStorage.setItem('vit_intelligence_disclaimer_v2', 'true');
    window.localStorage.setItem('vit_welcomed', 'true');
    window.localStorage.setItem('vit_onboarding_completed', 'true');
  });

  // Intercept the API call to /api/matches/40 to return a "partial" match missing intelligence
  await page.route('**/api/matches/40', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        match_id: 40,
        home_team: 'Test Home',
        away_team: 'Test Away',
        league: 'Test League',
        kickoff_time: '2026-06-28T12:00:00Z',
        odds: { home: 2.0, draw: 3.0, away: 3.5 },
        intelligence: null // Force frontend to use fallbacks
      }),
    });
  });

  await page.goto('http://localhost:5000/matches/40');

  // Verify page rendered despite missing intelligence
  await expect(page.locator('h1')).toContainText('Intelligence Terminal');
  await expect(page.locator('p')).toContainText('Test Home');
  await expect(page.locator('p')).toContainText('Test Away');

  // Take a screenshot
  await page.screenshot({ path: 'match_detail_fallback.png', fullPage: true });
});
