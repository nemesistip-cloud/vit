import { expect, test } from '@playwright/test'

const smokeEmail = process.env.VIT_SMOKE_EMAIL
const smokePassword = process.env.VIT_SMOKE_PASSWORD
const runAuthenticatedSmoke = process.env.VIT_RUN_AUTHENTICATED_SMOKE === 'true'

test('deployed gateway and VIT Chain read endpoints are healthy', async ({ request }) => {
  const [ping, readiness, chainStatus, recentBlocks, metrics, anonymousIdentity] = await Promise.all([
    request.get('/ping'),
    request.get('/ready'),
    request.get('/api/chain/status'),
    request.get('/api/chain/recent-blocks?limit=1'),
    request.get('/api/chain/metrics'),
    request.get('/api/auth/me'),
  ])

  expect(ping.status()).toBe(200)
  expect((await ping.json()).status).toBe('ok')
  expect(readiness.status()).toBe(200)
  expect((await readiness.json()).status).toBe('ready')

  expect(chainStatus.status()).toBe(200)
  const chainPayload = await chainStatus.json()
  expect(chainPayload.source).toBe('vit-chain')
  expect(chainPayload.authority).toBe('protocol')
  expect(chainPayload.data.chain_id).toBe(7764)
  expect(chainPayload.data.block_height).toBeGreaterThanOrEqual(0)

  expect(recentBlocks.status()).toBe(200)
  expect((await recentBlocks.json()).blocks.length).toBeGreaterThan(0)
  expect(metrics.status()).toBe(200)
  expect((await metrics.json()).active_validators).toBeGreaterThanOrEqual(0)
  expect(anonymousIdentity.status()).toBe(401)
})

test.describe('authenticated deployed smoke', () => {
  test.skip(
    !runAuthenticatedSmoke || !smokeEmail || !smokePassword,
    'Set VIT_RUN_AUTHENTICATED_SMOKE=true and provide VIT_SMOKE_EMAIL and VIT_SMOKE_PASSWORD to enable production login',
  )

  test('admin login establishes an authenticated identity without exposing its token', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="text"]').first().fill(smokeEmail!)
    await page.locator('input[type="password"]').fill(smokePassword!)
    await page.locator('form').getByRole('button', { name: 'Sign In' }).click()
    await page.waitForURL(url => !url.pathname.endsWith('/login'))

    const identity = await page.evaluate(async () => {
      const token = localStorage.getItem('vit_token')
      if (!token) return { tokenStored: false, tokenInUrl: false, status: 0, role: null }

      const response = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const user = await response.json()
      return {
        tokenStored: true,
        tokenInUrl: window.location.href.includes(token),
        status: response.status,
        role: user.role,
      }
    })

    expect(identity.tokenStored).toBe(true)
    expect(identity.tokenInUrl).toBe(false)
    expect(identity.status).toBe(200)
    expect(['admin', 'super_admin']).toContain(identity.role)
  })
})