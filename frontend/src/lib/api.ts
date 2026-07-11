/**
 * api.ts — VIT Platform API Client
 *
 * Phase 0: Service URLs are resolved from the registry singleton instead
 * of being hardcoded. Call bootstrapRegistry() before using any api method
 * (done in main.tsx on app startup).
 *
 * Direct imports of ENDPOINTS are still exported for backwards-compat with
 * any page that already uses them — they remain live references into the
 * registry so they update automatically after bootstrap.
 */

import { registry } from '@/lib/registry'

/** Live URL accessors — always read from the registry singleton. */
export const ENDPOINTS = {
  get gateway() { return registry.get('gateway') },
  get ai()      { return registry.get('ai') },
  get storage() { return registry.get('storage') },
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
  name?: string
  status: string
  version?: string
  environment?: string
  timestamp?: string
  uptime?: number | string
  services?: Record<string, unknown>
  redis?: { status: string; latency?: number }
  postgres?: { status: string; latency?: number }
  _latency?: number
}

export interface ServiceDiscovery {
  name: string
  url?: string
  status?: string
  version?: string
  latency_ms?: number
  reachable?: boolean
}

export interface GatewayServices {
  status?: string
  version?: string
  timestamp?: string
  services?: Record<string, ServiceDiscovery>
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
