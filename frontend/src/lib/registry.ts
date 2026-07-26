/**
 * registry.ts — VIT Platform Service Registry Client
 *
 * Phase 0: fetches /api/registry from the gateway on startup and calls
 * updateServiceUrls() in api.ts so every subsequent ENDPOINTS read uses the
 * live, server-declared URLs instead of the build-time fallbacks.
 *
 * Dependency direction: registry.ts → api.ts (never the reverse).
 *
 * Usage:
 *   import { bootstrapRegistry } from '@/lib/registry'
 *   void bootstrapRegistry()   // in main.tsx, before React render
 */

import { updateServiceUrls } from '@/lib/api'

// Empty string → relative URL → Vite dev proxy handles it.
// Production builds inject VITE_GATEWAY_URL as an absolute URL.
const GATEWAY_URL = (
  import.meta.env.VITE_GATEWAY_URL ?? ''
).replace(/\/$/, '')

// ── Payload shape from GET /api/registry ─────────────────────────────────────

export interface ServiceEntry {
  url: string
  status?: string
  version?: string
  latency_ms?: number
  reachable?: boolean
}

export interface RegistryPayload {
  status: string
  version: string
  timestamp: string
  services: Record<string, ServiceEntry>
}

// ── Bootstrap state ───────────────────────────────────────────────────────────

let _bootstrapped = false
let _bootstrapPromise: Promise<void> | null = null

// ── Public bootstrap function ─────────────────────────────────────────────────

/**
 * Fetch the gateway service registry and push live URLs into api.ts.
 * Safe to call multiple times — only runs the network request once.
 * Falls back to build-time defaults if the network call fails.
 */
export function bootstrapRegistry(): Promise<void> {
  if (_bootstrapped) return Promise.resolve()
  if (_bootstrapPromise !== null) return _bootstrapPromise

  _bootstrapPromise = _doBootstrap()
  return _bootstrapPromise
}

async function _doBootstrap(): Promise<void> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)

    const res = await fetch(`${GATEWAY_URL}/api/registry`, {
      signal: controller.signal,
    })
    clearTimeout(timeout)

    if (!res.ok) {
      console.warn("bootstrapRegistry: /api/registry returned non-OK status", res.status, res.statusText)
      _bootstrapped = true
      return
    }

    const data: RegistryPayload = await res.json()

    if (data.services) {
      const urls: { gateway?: string; ai?: string; storage?: string } = {}
      for (const [name, entry] of Object.entries(data.services)) {
        if (entry.url) {
          const clean = entry.url.replace(/\/$/, '')
          if (name === 'gateway')    urls.gateway = clean
          else if (name === 'ai')    urls.ai      = clean
          else if (name === 'storage') urls.storage = clean
        }
      }
      updateServiceUrls(urls)
    }

    _bootstrapped = true
  } catch (err) {
    // Network unavailable — build-time defaults in api.ts are used-as-is
    // Log a visible warning so developers see why service discovery failed.
    // This helps diagnose auth/register issues when the gateway URL isn't reachable.
    // eslint-disable-next-line no-console
    console.warn("bootstrapRegistry: failed to fetch /api/registry — using build-time defaults", err)
    _bootstrapped = true
  }
}
