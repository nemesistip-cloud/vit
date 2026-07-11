/**
 * registry.ts — VIT Platform Service Registry Client
 *
 * Phase 0: every frontend page discovers service URLs from the gateway
 * registry instead of hardcoding them. When a service moves hosts, only
 * VIT_*_URL env vars need updating — nothing in the frontend changes.
 *
 * Usage:
 *   import { registry } from '@/lib/registry'
 *   const aiUrl = registry.get('ai')
 */

const GATEWAY_URL = (
  import.meta.env.VITE_GATEWAY_URL ?? 'https://vitnetwork-nls4.onrender.com'
).replace(/\/$/, '')

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

// ── Internal singleton state ──────────────────────────────────────────────────

let _registry: Record<string, string> = {
  gateway:    GATEWAY_URL,
  ai:         'https://vit-ai.onrender.com',
  storage:    'https://vit-storage-4trt.onrender.com',
  blockchain: GATEWAY_URL,
  wallet:     GATEWAY_URL,
}

let _health: Record<string, ServiceEntry> = {}
let _bootstrapped = false
let _bootstrapPromise: Promise<void> | null = null

// ── Bootstrap (called once at app startup) ────────────────────────────────────

export async function bootstrapRegistry(): Promise<void> {
  if (_bootstrapped) return
  if (_bootstrapPromise) return _bootstrapPromise

  _bootstrapPromise = (async () => {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 5000)

      const res = await fetch(`${GATEWAY_URL}/api/registry`, {
        signal: controller.signal,
      })
      clearTimeout(timeout)

      if (!res.ok) return

      const data: RegistryPayload = await res.json()

      if (data.services) {
        const updated: Record<string, string> = { ..._registry }
        const health: Record<string, ServiceEntry> = {}

        for (const [name, entry] of Object.entries(data.services)) {
          if (entry.url) updated[name] = entry.url.replace(/\/$/, '')
          health[name] = entry
        }

        _registry = updated
        _health   = health
      }

      _bootstrapped = true
    } catch {
      // Network unavailable — fall back to defaults already set above
      _bootstrapped = true
    }
  })()

  return _bootstrapPromise
}

// ── Public API ────────────────────────────────────────────────────────────────

export const registry = {
  /** Return the base URL for a named service. */
  get(service: string): string {
    return _registry[service] ?? GATEWAY_URL
  },

  /** Return the last-known health entry for a service. */
  health(service: string): ServiceEntry | undefined {
    return _health[service]
  },

  /** Full snapshot of all resolved URLs. */
  all(): Record<string, string> {
    return { ..._registry }
  },

  /** Full snapshot of all health entries. */
  allHealth(): Record<string, ServiceEntry> {
    return { ..._health }
  },

  /** Whether bootstrapRegistry() has completed. */
  ready(): boolean {
    return _bootstrapped
  },
}
