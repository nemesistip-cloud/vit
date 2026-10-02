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

test('prediction history distinguishes an API failure from an empty history', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'playwright-test-placeholder');
    localStorage.setItem('vit_user', JSON.stringify({ id: 7, username: 'test-user', role: 'user' }));
  });

  await page.route('**/api/predict/history**', route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'temporarily unavailable' }),
  }));
  await page.route('**/api/predict/accuracy', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total: 0, win_rate: 0, current_streak: 0 }),
  }));
  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ verified: true }),
  }));

  await page.goto('/predictions');

  await expect(page.getByRole('alert')).toContainText('Predictions could not be loaded');
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  await expect(page.getByText('No predictions yet')).toHaveCount(0);
});

test('prediction accuracy labels its settled denominator', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'playwright-test-placeholder');
    localStorage.setItem('vit_user', JSON.stringify({ id: 7, username: 'test-user', role: 'user' }));
  });

  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ verified: true }),
  }));
  await page.route('**/api/predict/history**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([]),
  }));
  await page.route('**/api/predict/accuracy', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ total: 7, settled: 6, win_rate: 0.833, current_streak: 3, best_league: 'League B' }),
  }));

  await page.goto('/predictions');

  await expect(page.getByText('Settled / Total')).toBeVisible();
  await expect(page.getByText('6 / 7', { exact: true })).toBeVisible();
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

test('admin feature flag creates a config row when none exists', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'admin-feature-flag-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 42, username: 'operator', role: 'super_admin' }));
  });

  let savedFlag: { key: string; value: boolean } | undefined;
  await page.route('**/api/admin/config', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(savedFlag ? [savedFlag] : []),
      });
      return;
    }

    const request = route.request();
    savedFlag = request.postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, key: savedFlag.key }),
    });
  });

  await page.goto('/admin');
  await page.getByRole('button', { name: 'Config' }).nth(0).click();
  await page.getByRole('button', { name: 'Predictions enabled' }).click();

  await expect(page.getByRole('button', { name: 'Predictions disabled' })).toBeVisible();
  expect(savedFlag).toEqual({ key: 'predictions_enabled', value: false, description: 'Feature flag predictions_enabled' });
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

test('genesis stage seven requires explicit confirmation for the legacy mint exception', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'genesis-legacy-admin-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 1, username: 'genesis-admin', role: 'super_admin' }));
  });

  let accepted = false;
  let submittedBody: Record<string, string> | undefined;
  await page.route('**/api/genesis/status', route => {
    const validationResults = Object.fromEntries(Array.from({ length: 10 }, (_, index) => {
      const stage = index + 1;
      return [String(stage), {
        stage,
        passed: stage !== 7 || accepted,
        reason: stage === 7
          ? accepted ? 'Existing genesis accepted under a super-admin legacy exception; 2-of-3 signer evidence is not claimed' : 'An existing genesis mint was found; explicit super-admin legacy acceptance is required'
          : 'Live check passed',
      }];
    }));
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_stage: 7,
        completed_stages: accepted ? [1, 2, 3, 4, 5, 6, 7] : [1, 2, 3, 4, 5, 6],
        total_stages: 10,
        status: 'bootstrapping',
        verified: false,
        dependency_status: { database: true, redis: true },
        validation_results: validationResults,
      }),
    });
  });
  await page.route('**/api/genesis/accept-existing-mint', async route => {
    submittedBody = route.request().postDataJSON();
    accepted = true;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ accepted: true, new_mint_submitted: false }) });
  });

  await page.goto('/genesis');

  const acceptButton = page.getByRole('button', { name: 'Record legacy exception' });
  await expect(acceptButton).toBeVisible();
  await expect(page.getByText('Genesis mint acceptance recorded', { exact: true })).toBeVisible();
  await expect(page.getByText('AI model registry and gateway configured', { exact: true })).toBeVisible();
  await expect(acceptButton).toBeDisabled();
  await page.getByLabel('Decision reason').fill('Authorized acceptance of the existing block-zero mint without verified two-of-three evidence; do not mint again.');
  await expect(acceptButton).toBeDisabled();
  await page.getByLabel('Type ACCEPT EXISTING GENESIS MINT').fill('ACCEPT EXISTING GENESIS MINT');
  await expect(acceptButton).toBeEnabled();
  await acceptButton.click();

  await expect.poll(() => submittedBody).toEqual({
    confirmation: 'ACCEPT EXISTING GENESIS MINT',
    reason: 'Authorized acceptance of the existing block-zero mint without verified two-of-three evidence; do not mint again.',
  });
  await expect(page.getByText('Passed', { exact: true }).first()).toBeVisible();
});

test('subscription page renders live catalog and starts the matching yearly checkout', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'subscription-contract-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 7, username: 'subscriber', role: 'user' }));
  });

  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ verified: true }),
  }));
  await page.route('**/api/subscription/plans', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ plans: [
      { name: 'free', display_name: 'Free', price_monthly: 0, price_yearly: 0, description: 'Basic predictions', features: { predictions: true } },
      { name: 'analyst', display_name: 'Analyst', price_monthly: 49, price_yearly: 441, description: 'Prediction analytics', features: { predictions: true, advanced_analytics: true } },
    ] }),
  }));
  await page.route('**/api/subscription/my-plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ plan: { name: 'free', display_name: 'Free' }, subscription: { status: 'active' }, usage: {} }),
  }));

  let checkoutBody: Record<string, string> | undefined;
  await page.route('**/api/subscription/create-checkout', async route => {
    checkoutBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ checkout_url: 'https://checkout.paystack.com/test-reference', reference: 'test-reference' }),
    });
  });
  await page.route('https://checkout.paystack.com/**', route => route.fulfill({ status: 200, contentType: 'text/html', body: 'Checkout test' }));

  await page.goto('/subscription');
  await expect(page.getByRole('heading', { name: 'Analyst' })).toBeVisible();
  await expect(page.getByText('$49', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'yearly' }).click();
  await expect(page.getByText('$441', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to checkout' }).click();
  await expect.poll(() => checkoutBody).toEqual({ plan: 'analyst', billing: 'yearly' });
});

test('subscription page shows catalog errors instead of invented fallback pricing', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vit_token', 'subscription-error-token');
    localStorage.setItem('vit_user', JSON.stringify({ id: 7, username: 'subscriber', role: 'user' }));
  });
  await page.route('**/api/genesis/status', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ verified: true }),
  }));
  await page.route('**/api/subscription/plans', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'unavailable' }) }));

  await page.goto('/subscription');

  await expect(page.getByRole('alert')).toContainText('No fallback prices are shown');
  await expect(page.getByRole('button', { name: 'Continue to checkout' })).toHaveCount(0);
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
