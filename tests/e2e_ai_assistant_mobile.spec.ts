import { test, expect, devices } from '@playwright/test';

test.use({
  ...devices['Pixel 5'],
  baseURL: 'http://127.0.0.1:5000',
});

test.describe('AI Assistant Capability Surface - Mobile Chrome Headless', () => {
  test.beforeEach(async ({ page }) => {
    // Dismiss terminal disclaimer & set mock auth state
    await page.addInitScript(() => {
      localStorage.setItem('vit_intelligence_disclaimer_v2', 'true');
      localStorage.setItem('vit_token', 'mock_jwt_token');
      localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'tester', role: 'user' }));
    });

    // Mock AI Assistant endpoint for full capability surface
    await page.route('**/api/ai/assistant/chat', async (route, request) => {
      const postData = JSON.parse(request.postData() || '{}');
      const msg = (postData.message || '').toLowerCase().trim();

      if (msg === '') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Message cannot be empty.' }),
        });
        return;
      }

      if (msg === 'hi') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            available: true,
            response: 'Hello! I am the VIT AI Assistant. How can I assist you with prediction markets or sports intelligence today?',
            model_id: 'llm_consensus_v1',
            thoughts: ['Greeting routed to conversational layer'],
          }),
        });
        return;
      }

      if (msg.includes('what can you do')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            available: true,
            response: 'I can analyze upcoming football matches, compute ensemble forecasts, assist with governance voting, track wallet balances, and answer platform queries.',
            model_id: 'llm_consensus_v1',
            thoughts: ['Capability summary generated'],
          }),
        });
        return;
      }

      if (msg.includes('who won the 2022 world cup')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            available: true,
            response: 'Argentina won the 2022 FIFA World Cup in Qatar, defeating France on penalties after a dramatic 3-3 draw.',
            model_id: 'llm_consensus_v1',
            thoughts: ['Football trivia query processed'],
          }),
        });
        return;
      }

      if (msg.includes('predict match arsenal vs chelsea')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            available: true,
            response: '### Tactical Forecast: Arsenal vs Chelsea\n- **Home Win (Arsenal):** 52.4%\n- **Draw:** 26.1%\n- **Away Win (Chelsea):** 21.5%\n- **Confidence:** 82.0%',
            model_id: 'ensemble_v1',
            thoughts: ['Sports match lookup and forecast generated'],
          }),
        });
        return;
      }

      if (msg.includes('features') || msg.includes('home_prob')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            available: true,
            response: 'Structured prediction features received. Master Ensemble (ensemble_v1) evaluated Home Win probability at 61.2%.',
            model_id: 'ensemble_v1',
            thoughts: ['Feature matrix prediction executed via ensemble_v1'],
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          available: true,
          response: `Received query: "${postData.message}".`,
          model_id: 'llm_consensus_v1',
        }),
      });
    });

    await page.goto('/assistant');
  });

  test('Renders Assistant Mobile UI correctly', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('VIT AI Assistant');
    await expect(page.getByPlaceholder(/Ask anything about VIT Network/i)).toBeVisible();
  });

  test('Handles Conversational Greeting "Hi"', async ({ page }) => {
    const input = page.getByPlaceholder(/Ask anything about VIT Network/i);
    await input.fill('Hi');
    await page.click('button:has(svg.lucide-send)');

    await expect(page.getByText('Hello! I am the VIT AI Assistant')).toBeVisible();
  });

  test('Handles Capability Query "What can you do?"', async ({ page }) => {
    const input = page.getByPlaceholder(/Ask anything about VIT Network/i);
    await input.fill('What can you do?');
    await page.click('button:has(svg.lucide-send)');

    await expect(page.getByText('I can analyze upcoming football matches')).toBeVisible();
  });

  test('Handles Football Trivia Question', async ({ page }) => {
    const input = page.getByPlaceholder(/Ask anything about VIT Network/i);
    await input.fill('Who won the 2022 World Cup?');
    await page.click('button:has(svg.lucide-send)');

    await expect(page.getByText('Argentina won the 2022 FIFA World Cup')).toBeVisible();
  });

  test('Handles Match Prediction Query', async ({ page }) => {
    const input = page.getByPlaceholder(/Ask anything about VIT Network/i);
    await input.fill('predict match Arsenal vs Chelsea');
    await page.click('button:has(svg.lucide-send)');

    await expect(page.getByText('Tactical Forecast: Arsenal vs Chelsea')).toBeVisible();
  });

  test('Handles Structured Prediction Features Query', async ({ page }) => {
    const input = page.getByPlaceholder(/Ask anything about VIT Network/i);
    await input.fill('Evaluate features: home_prob 0.55 away_prob 0.25');
    await page.click('button:has(svg.lucide-send)');

    await expect(page.getByText('Structured prediction features received')).toBeVisible();
  });
});
