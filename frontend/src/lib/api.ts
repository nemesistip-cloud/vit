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
  // Attach latency — works for both objects and arrays
  if (Array.isArray(data)) return data as unknown as T
  return { ...data, _latency: latency } as T
}

// ---------- gateway ----------

export interface GatewayHealth {
  name?: string
  status: string
  version?: string
  environment?: string
  timestamp?: string
  uptime?: number
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

export const gatewayApi = {
  health:   (signal?: AbortSignal) => get<GatewayHealth>(`${ENDPOINTS.gateway}/health`, signal),
  status:   (signal?: AbortSignal) => get<Record<string, unknown>>(`${ENDPOINTS.gateway}/api/status`, signal),
  services: (signal?: AbortSignal) => get<{ services?: ServiceDiscovery[] }>(`${ENDPOINTS.gateway}/api/services`, signal),
}

// ---------- AI  (vit-ai.onrender.com, prefix: /api/v1) ----------

export interface AIHealth {
  status: string
  _latency?: number
}

export interface AIKernelStatus {
  status?: string
  mode?: string
  uptime?: string | number
  total_inferences?: number
  error_rate?: string | number
  avg_latency?: string | number
  latency?: number
  [key: string]: unknown
}

export interface Model {
  id: string
  name?: string
  provider?: string
  status?: string
  version?: string
  latest_version?: string
  description?: string
}

export interface Provider {
  name?: string
  id?: string
  status?: string
  health?: string
  type?: string
  models?: number
  latency?: number
}

export interface Feature {
  id: string
  name?: string
  type?: string
  [key: string]: unknown
}

export const aiApi = {
  health:    (signal?: AbortSignal) => get<AIHealth>(`${ENDPOINTS.ai}/health`, signal),
  version:   (signal?: AbortSignal) => get<{ version: string }>(`${ENDPOINTS.ai}/version`, signal),
  aiStatus:  (signal?: AbortSignal) => get<AIKernelStatus>(`${ENDPOINTS.ai}/api/v1/ai/status`, signal),
  providers: (signal?: AbortSignal) => get<Provider[]>(`${ENDPOINTS.ai}/api/v1/ai/providers`, signal),
  models:    (signal?: AbortSignal) => get<Model[]>(`${ENDPOINTS.ai}/api/v1/models`, signal),
  features:  (signal?: AbortSignal) => get<Feature[]>(`${ENDPOINTS.ai}/api/v1/features`, signal),
}

// ---------- Storage (vit-storage-4trt.onrender.com, tachyon) ----------

export interface StorageHealth {
  status: string
  version?: string
  plane?: string
  database?: string
  redis?: string
  capacity?: number
  used?: number
  objectCount?: number
  subsystems?: Record<string, unknown>
  _latency?: number
}

export interface TachyonStatus {
  status: string
  version?: string
  module?: string
  active_nodes?: number
  manifest_count?: number
  total_bytes?: number
  providers?: Record<string, unknown>
  _latency?: number
}

export interface StorageObject {
  key?: string
  file_id?: string
  filename?: string
  size?: number
  size_bytes?: number
  lastModified?: string
  created_at?: string
  contentType?: string
  content_type?: string
  url?: string
}

export interface StorageList {
  objects?: StorageObject[]
  manifests?: StorageObject[]
  total?: number
  [key: string]: unknown
}

export const storageApi = {
  health:        (signal?: AbortSignal) => get<StorageHealth>(`${ENDPOINTS.storage}/health`, signal),
  tachyonStatus: (signal?: AbortSignal) => get<TachyonStatus>(`${ENDPOINTS.storage}/api/v1/status`, signal),
  list:          (signal?: AbortSignal) => get<StorageList>(`${ENDPOINTS.storage}/api/v1/manifests`, signal),
  listAlt:       (signal?: AbortSignal) => get<StorageList>(`${ENDPOINTS.storage}/api/objects`, signal),
  metrics:       (signal?: AbortSignal) => get<unknown>(`${ENDPOINTS.storage}/metrics`, signal),
}
