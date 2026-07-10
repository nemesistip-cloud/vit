const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL ?? 'https://vitnetwork-nls4.onrender.com'
const AI_URL      = import.meta.env.VITE_AI_URL      ?? 'https://vit-ai.onrender.com'
const STORAGE_URL = import.meta.env.VITE_STORAGE_URL ?? 'https://vit-storage-4trt.onrender.com'

export const ENDPOINTS = {
  gateway: GATEWAY_URL.replace(/\/$/, ''),
  ai:      AI_URL.replace(/\/$/, ''),
  storage: STORAGE_URL.replace(/\/$/, ''),
}

// ---------- helpers ----------

async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const start = performance.now()
  const res   = await fetch(url, { signal })
  const latency = Math.round(performance.now() - start)
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)
  const data = await res.json()
  return { ...data, _latency: latency } as T
}

// ---------- gateway ----------

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

export interface GatewayServices {
  services?: ServiceDiscovery[]
  [key: string]: unknown
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

export const gatewayApi = {
  health:   (signal?: AbortSignal) => get<GatewayHealth>(`${ENDPOINTS.gateway}/health`, signal),
  services: (signal?: AbortSignal) => get<GatewayServices>(`${ENDPOINTS.gateway}/api/services`, signal),
  status:   (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.gateway}/api/status`, signal),
  metrics:  (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.gateway}/api/metrics`, signal),
}

// ---------- AI ----------

export interface AIHealth {
  status: string
  version?: string
  models?: Model[]
  providers?: Provider[]
  inference?: { status: string; latency?: number }
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

export interface AIModels {
  models?: Model[]
  [key: string]: unknown
}

export const aiApi = {
  health:  (signal?: AbortSignal) => get<AIHealth>(`${ENDPOINTS.ai}/health`, signal),
  models:  (signal?: AbortSignal) => get<AIModels>(`${ENDPOINTS.ai}/api/models`, signal),
  status:  (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.ai}/api/status`, signal),
}

// ---------- Storage ----------

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

export const storageApi = {
  health:  (signal?: AbortSignal) => get<StorageHealth>(`${ENDPOINTS.storage}/health`, signal),
  list:    (signal?: AbortSignal) => get<StorageList>(`${ENDPOINTS.storage}/api/objects`, signal),
  metrics: (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.storage}/api/metrics`, signal),
}
