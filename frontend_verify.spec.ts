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

test('admin console shows a production summary and editable feature flags', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'admin-ui-smoke-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'operator', role: 'admin' }));
  });

  await page.goto('/admin');
  await expect(page.getByText('Operations overview', { exact: false })).toBeVisible();
  await expect(page.getByText('Operational feeds')).toBeVisible();
  await expect(page.getByText('99.98% uptime')).toHaveCount(0);
  await expect(page.getByText('API burst spike')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^Predictions$/i })).toBeVisible();

  await page.getByRole('button', { name: 'Config' }).nth(0).click();
  const mainPanel = page.locator('main');
  await expect(mainPanel.getByText('Feature flags', { exact: false })).toBeVisible();
  await expect(mainPanel.getByText('Predictions', { exact: true }).first()).toBeVisible();
  await expect(mainPanel.getByRole('button', { name: /Predictions (enabled|disabled)/i }).first()).toBeVisible();

  await page.screenshot({ path: 'admin-console-ux.png' });
});

test('admin Users and System tabs render authorized read data', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'admin-read-only-test-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 42, username: 'operator', role: 'super_admin' }));
  });

  const authorizedReads: string[] = [];
  await page.route('**/api/admin/users?limit=50', async route => {
    authorizedReads.push(route.request().headers().authorization ?? '');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total: 1,
        users: [{ id: 42, username: 'operator', email: 'operator@example.test', role: 'super_admin', is_active: true }],
      }),
    });
  });
  await page.route('**/api/admin/system/health', async route => {
    authorizedReads.push(route.request().headers().authorization ?? '');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        version: '1.2.0',
        database: { status: 'connected' },
        redis: { status: 'connected' },
        models_ready: 13,
      }),
    });
  });
  await page.route('**/api/admin/system/metrics', async route => {
    authorizedReads.push(route.request().headers().authorization ?? '');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ requests_24h: 10, errors_24h: 0, error_rate_pct: 0, avg_response_ms: 24 }),
    });
  });
  await page.route('**/api/system/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total_users: 42, active_users_30d: 10, active_validators: 0, total_predictions: 100 }),
  }));

  await page.goto('/admin');
  await page.getByRole('button', { name: 'Users', exact: true }).click();
  await expect(page.getByText('operator@example.test')).toBeVisible();

  await page.getByRole('button', { name: 'System', exact: true }).click();
  await expect(page.getByText('Connected', { exact: true })).toBeVisible();
  await expect(page.getByText('42', { exact: true })).toBeVisible();
  expect(authorizedReads.length).toBeGreaterThanOrEqual(3);
  expect(authorizedReads.every(value => value.startsWith('Bearer '))).toBe(true);
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

test('authenticated mobile navigation starts with workspace actions', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'ui-mobile-nav-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'operator', role: 'user' }));
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/dashboard');
  await page.getByRole('button', { name: /open menu/i }).click();

  const menu = page.locator('header').getByText('Workspace', { exact: true });
  await expect(menu).toBeVisible();
  await expect(page.locator('header').getByText('Explore', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
});

test('genesis initialization wizard exposes the bootstrap stages and readiness flow', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'genesis-wizard-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'genesis-admin', role: 'admin' }));
  });

  await page.goto('/genesis');

  await expect(page.getByRole('heading', { name: /Genesis Initialization Wizard/i })).toBeVisible();
  await expect(page.getByText(/Stage 1: Platform Configuration/i)).toBeVisible();
  await expect(page.getByText(/Stage 7: Genesis VIT Coin Mint/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /Advance to next stage/i })).toBeVisible();
});

test('genesis wizard hydrates live bootstrap state from the backend', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'genesis-status-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'genesis-admin', role: 'admin' }));
  });

  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      current_stage: 10,
      completed_stages: [1, 2, 3, 4, 5, 6, 7, 8, 9],
      total_stages: 10,
      status: 'verified',
      verified: true,
      updated_at: '2026-09-30T00:00:00Z',
      dependency_status: { database: true, redis: true },
      validation_results: Object.fromEntries(Array.from({ length: 10 }, (_, index) => [
        String(index + 1), { stage: index + 1, passed: true, reason: 'Live check passed' },
      ])),
    }),
  }));

  await page.goto('/genesis');

  await expect(page.getByText(/Current stage/i)).toBeVisible();
  await expect(page.getByRole('heading', { name: /Mainnet Readiness Verification/i })).toBeVisible();
  await expect(page.getByText(/verified/i).first()).toBeVisible();
});

test('genesis wizard shows the live validation result and reason for the active stage', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'genesis-validation-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'genesis-admin', role: 'admin' }));
  });

  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      current_stage: 2,
      completed_stages: [1],
      total_stages: 10,
      status: 'bootstrapping',
      verified: false,
      updated_at: '2026-09-30T00:00:00Z',
      dependency_status: { database: true, redis: true },
      validation_results: {
        '1': { stage: 1, passed: true, reason: 'Platform runtime configuration is valid' },
        '2': { stage: 2, passed: false, reason: 'DID resolver endpoint and validator schema must be configured' },
      },
    }),
  }));

  await page.goto('/genesis');

  await expect(page.getByText(/Validation gate/i)).toBeVisible();
  await expect(page.getByText('DID resolver endpoint and validator schema must be configured', { exact: true })).toBeVisible();
  await expect(page.getByText(/Stage 2: Identity Configuration/i)).toBeVisible();
  await expect(page.getByText('Blocked', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Mark stage complete/i })).toHaveCount(0);
});

test('platform blocks authenticated access until genesis verification is complete', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'boot-gate-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'boot-gate-admin', role: 'admin' }));
  });

  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      current_stage: 9,
      completed_stages: [1, 2, 3, 4, 5, 6, 7, 8],
      total_stages: 10,
      status: 'bootstrapping',
      verified: false,
      updated_at: '2026-09-30T00:00:00Z',
    }),
  }));

  await page.goto('/dashboard');

  await expect(page).toHaveURL(/\/genesis$/);
  await expect(page.getByRole('heading', { name: /Genesis Initialization Wizard/i })).toBeVisible();
});

test('chain explorer interprets Unix-second block timestamps correctly', async ({ page }) => {
  const timestamp = Math.floor(Date.now() / 1000) - 5;
  await page.route('**/api/chain/height', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ height: 24981, chain_id: 7764 }),
  }));
  await page.route('**/api/chain/recent-blocks**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ blocks: [{ height: 24981, block_hash: 'hash', timestamp, tx_count: 0 }] }),
  }));
  await page.route('**/api/chain/metrics', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ tps: 0, total_transactions: 0, active_validators: 0 }),
  }));
  await page.route('**/api/chain/transactions**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ transactions: [] }),
  }));

  await page.goto('/chain');

  await expect(page.getByText(/Block #24,981/).first()).toBeVisible();
  await expect(page.getByText(/\d+s ago/).first()).toBeVisible();
});

test('AI overview does not invent accuracy for models without measurements', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'ai-accuracy-test-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'tester', role: 'user' }));
  });
  await page.route('**/api/registry', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ services: { ai: { status: 'healthy', version: '1.0', models_loaded: 1 } } }),
  }));
  await page.route('**/api/dashboard/model-confidence', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ models: [{ name: 'Measured Model', accuracy: 63.5 }, { name: 'Unmeasured Model', accuracy: null }] }),
  }));
  await page.route('**/api/ai-feed/health', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 'healthy', models_loaded: 1 }),
  }));
  await page.route('**/api/ai-feed/models', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      registered_count: 2,
      models: [
        { id: 'model-a', name: 'Model A', provider: 'native' },
        { id: 'model-b', name: 'Model B', provider: 'native' },
      ],
    }),
  }));
  await page.route('**/api/ai-feed/sources', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([]),
  }));

  await page.goto('/ai');

  await expect(page.getByRole('heading', { name: 'Historical Model Accuracy' })).toBeVisible();
  await expect(page.getByText('Measured Model')).toBeVisible();
  await expect(page.getByText('63.5%')).toBeVisible();
  await expect(page.getByText('Unmeasured Model')).toHaveCount(0);
  await expect(page.getByText('75.0%')).toHaveCount(0);

  await page.getByRole('button', { name: 'models', exact: true }).click();
  await expect(page.getByText('2 registered · 1 loaded in runtime')).toBeVisible();
  await expect(page.getByText('Model A')).toBeVisible();
  await expect(page.getByText('Registered', { exact: true }).first()).toBeVisible();
});

test('human status page is separate from the legacy machine status route', async ({ page }) => {
  await page.goto('/status-page');

  await expect(page.getByRole('heading', { name: 'Platform Health' })).toBeVisible();
});

test('Developer Hub documents the deployed Chain service and gateway health schema', async ({ page }) => {
  await page.goto('/developers');

  await expect(page.getByText('vit-chain', { exact: true })).toBeVisible();
  await expect(page.getByText(/models_loaded/)).toBeVisible();
  await expect(page.getByText(/blockchain service \(future\)/i)).toHaveCount(0);
});
