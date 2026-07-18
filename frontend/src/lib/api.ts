/**
 * api.ts — VIT Platform API Client
 *
 * Phase 0: service URLs are stored as mutable let variables and updated by
 * bootstrapRegistry() (in registry.ts) on app startup. ENDPOINTS exposes
 * them as getter properties so every subsequent read gets the live value.
 *
 * registry.ts calls updateServiceUrls() after the /api/registry fetch.
 * Nothing in this file imports from registry.ts — dependency is one-way.
 */

// ── Internal mutable service URLs ─────────────────────────────────────────────
// Defaults come from Vite env vars (set at build time) or hardcoded fallbacks.

// In dev (no VITE_GATEWAY_URL set) use an empty string so API calls are
// relative — the Vite dev proxy will forward them to localhost:8000.
// In production the build injects the real absolute URL.
let _gatewayUrl = (import.meta.env.VITE_GATEWAY_URL ?? '').replace(/\/$/, '')
let _aiUrl      = (import.meta.env.VITE_AI_URL      ?? '').replace(/\/$/, '')
let _storageUrl = (import.meta.env.VITE_STORAGE_URL ?? '').replace(/\/$/, '')

/**
 * Live URL accessors. Getter properties ensure that code reading
 * ENDPOINTS.gateway always gets the most-recently bootstrapped value.
 */
export const ENDPOINTS = {
  get gateway() { return _gatewayUrl },
  get ai()      { return _aiUrl },
  get storage() { return _storageUrl },
}

/**
 * Called by registry.ts after a successful /api/registry fetch.
 * Updates the internal URL state so all subsequent ENDPOINTS reads are live.
 */
export function updateServiceUrls(urls: { gateway?: string; ai?: string; storage?: string }): void {
  if (urls.gateway) _gatewayUrl = urls.gateway
  if (urls.ai)      _aiUrl      = urls.ai
  if (urls.storage) _storageUrl = urls.storage
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const start = performance.now()
  const res   = await fetch(url, { signal })
  const latency = Math.round(performance.now() - start)
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)
  const data = await res.json()
  return { ...data, _latency: latency } as T
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
  capacity?: number
  used?: number
  objectCount?: number
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
