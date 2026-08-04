/**
 * api.ts — VIT Platform API Client
 *
 * Phase 0: service URLs are stored as mutable let variables and updated by
 * bootstrapRegistry() (in registry.ts) on app startup. ENDPOINTS exposes
 * them as getter properties so every subsequent read gets the live value.
 *
 * Phase 1: Added vit-chain endpoint, request timeout (10 s), and 1-retry
 * logic for transient network errors.
 */

// ── Internal mutable service URLs ─────────────────────────────────────────────
let _gatewayUrl = (import.meta.env.VITE_GATEWAY_URL ?? '').replace(/\/$/, '')
let _aiUrl      = (import.meta.env.VITE_AI_URL      ?? '').replace(/\/$/, '')
let _storageUrl = (import.meta.env.VITE_STORAGE_URL ?? '').replace(/\/$/, '')
let _chainUrl   = (import.meta.env.VITE_CHAIN_URL   ?? 'https://vit-chain.onrender.com').replace(/\/$/, '')

/**
 * Live URL accessors. Getter properties ensure that code reading
 * ENDPOINTS.* always gets the most-recently bootstrapped value.
 */
export const ENDPOINTS = {
  get gateway() { return _gatewayUrl },
  get ai()      { return _aiUrl },
  get storage() { return _storageUrl },
  get chain()   { return _chainUrl },
}

/**
 * Called by registry.ts after a successful /api/registry fetch.
 * Updates the internal URL state so all subsequent ENDPOINTS reads are live.
 */
export function updateServiceUrls(urls: {
  gateway?: string
  ai?: string
  storage?: string
  chain?: string
}): void {
  if (urls.gateway) _gatewayUrl = urls.gateway
  if (urls.ai)      _aiUrl      = urls.ai
  if (urls.storage) _storageUrl = urls.storage
  if (urls.chain)   _chainUrl   = urls.chain
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

const TIMEOUT_MS = 10_000

/**
 * GET with latency tracking, 10-second timeout, and one automatic retry on
 * network failure (not on 4xx/5xx — those are real errors).
 */
async function get<T>(url: string, signal?: AbortSignal, attempt = 0): Promise<T> {
  const controller = new AbortController()
  const timer      = setTimeout(() => controller.abort(), TIMEOUT_MS)

  // Merge caller's signal with our timeout signal
  const combined = signal
    ? (() => {
        const ac = new AbortController()
        signal.addEventListener('abort', () => ac.abort())
        controller.signal.addEventListener('abort', () => ac.abort())
        return ac.signal
      })()
    : controller.signal

  const start = performance.now()
  try {
    const res = await fetch(url, { signal: combined })
    clearTimeout(timer)
    const latency = Math.round(performance.now() - start)
    // H4 fix: 401 auto-logout — expired/invalid token detected server-side
    if (res.status === 401) {
      try {
        const { clearAuth } = await import('@/hooks/useAuth')
        clearAuth()
      } catch { /* no-op if module not available */ }
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login?reason=session_expired'
      }
    }
    if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)
    const data = await res.json()
    return { ...data, _latency: latency } as T
  } catch (err: unknown) {
    clearTimeout(timer)
    // Retry once on network/timeout error (not on abort from caller)
    const isAbortedByCaller = signal?.aborted
    const isNetworkError    = err instanceof TypeError || (err instanceof DOMException && err.name === 'AbortError')
    if (!isAbortedByCaller && isNetworkError && attempt === 0) {
      return get<T>(url, signal, 1)
    }
    throw err
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface GatewayHealth {
  name: string
  status: string
  version: string
  environment: string
  timestamp?: string
  uptime?: number
  services?: Record<string, unknown>
  redis?: { status: string; latency?: number }
  postgres?: { status: string; latency?: number }
  _latency?: number
}

export interface ServiceDiscovery {
  name: string
  version?: string
  health?: string
  responseTime?: number
  dependencies?: string[]
  lastHeartbeat?: string
  url?: string
}

export interface GatewayServices {
  services?: ServiceDiscovery[]
  [key: string]: unknown
}

export interface PlatformStatus {
  status: string
  version?: string
  timestamp?: string
  services?: {
    gateway?: Record<string, unknown>
    ai?: Record<string, unknown>
    storage?: Record<string, unknown>
  }
  infrastructure?: {
    database?: { status: string }
    redis?: { status: string }
  }
  _latency?: number
}

export interface Model {
  id: string
  name?: string
  provider?: string
  status?: string
  latency?: number
}

export interface Provider {
  name: string
  status: string
  models?: number
  latency?: number
}

export interface AIHealth {
  status: string
  version?: string
  models_loaded?: number
  models?: Model[]
  providers?: Provider[]
  inference?: { status: string; latency?: number }
  _latency?: number
}

export interface AIModels {
  models?: Model[]
  [key: string]: unknown
}

export interface StorageHealth {
  status: string
  version?: string
  plane?: string
  capacity?: number
  used?: number
  objectCount?: number
  providers?: { active: number; available: number; disabled: number }
  database?: string
  redis?: string
  _latency?: number
}

export interface StorageObject {
  key: string
  size: number
  lastModified?: string
  contentType?: string
  url?: string
}

export interface StorageList {
  objects?: StorageObject[]
  total?: number
  [key: string]: unknown
}

export interface ChainHealth {
  status: string
  version?: string
  chain_id?: number
  network?: string
  block_height?: number
  peer_count?: number
  is_syncing?: boolean
  _latency?: number
}

export interface ChainBlock {
  index: number
  hash: string
  timestamp: string
  validator?: string
  tx_count?: number
  size?: number
}

export interface ChainBlocks {
  blocks?: ChainBlock[]
  total?: number
  [key: string]: unknown
}

// ── API clients ───────────────────────────────────────────────────────────────

export const gatewayApi = {
  health:   (signal?: AbortSignal) => get<GatewayHealth>(`${ENDPOINTS.gateway}/health`, signal),
  registry: (signal?: AbortSignal) => get<GatewayServices>(`${ENDPOINTS.gateway}/api/registry`, signal),
  services: (signal?: AbortSignal) => get<GatewayServices>(`${ENDPOINTS.gateway}/api/registry`, signal),
  status:   (signal?: AbortSignal) => get<PlatformStatus>(`${ENDPOINTS.gateway}/api/status`, signal),
  metrics:  (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.gateway}/api/metrics`, signal),
}

export const aiApi = {
  health:  (signal?: AbortSignal) => get<AIHealth>(`${ENDPOINTS.ai}/health`, signal),
  models:  (signal?: AbortSignal) => get<AIModels>(`${ENDPOINTS.ai}/api/v1/models`, signal),
  status:  (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.ai}/api/v1/ai/status`, signal),
}

export const storageApi = {
  health:  (signal?: AbortSignal) => get<StorageHealth>(`${ENDPOINTS.storage}/health`, signal),
  list:    (signal?: AbortSignal) => get<StorageList>(`${ENDPOINTS.storage}/api/v1/files`, signal),
  metrics: (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.storage}/metrics`, signal),
}

export const chainApi = {
  ping:   (signal?: AbortSignal) => get<ChainHealth>(`${ENDPOINTS.chain}/ping`, signal),
  health: (signal?: AbortSignal) => get<ChainHealth>(`${ENDPOINTS.chain}/ping`, signal),
  blocks: (signal?: AbortSignal) => get<ChainBlocks>(`${ENDPOINTS.chain}/api/blocks?limit=5`, signal),
  status: (signal?: AbortSignal) => get<ChainHealth>(`${ENDPOINTS.chain}/ping`, signal),
}
